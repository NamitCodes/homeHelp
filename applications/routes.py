import os
import json
from flask import redirect, render_template, url_for, request,flash,session, send_from_directory
from app import app
from applications.models import *
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, desc, func

from werkzeug.utils import secure_filename



ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

ALLOWED_EXTENSIONS_FOR_DOCS = {'pdf'}

def allowed_docs(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_FOR_DOCS

@app.route('/')
def home():
    if session.get('role') == 'admin':
        return redirect('/admin')
    
    # unique categories from Service table
    categories = Service.query.with_entities(Service.category).distinct().all()
    unique_categories = [category[0] for category in categories]

    dict_category_path = {}

    for category in unique_categories:
        service_with_image = Service.query.filter_by(category=category).first()
        
        if service_with_image and service_with_image.image:
            dict_category_path[category] = service_with_image.image
        else:
            dict_category_path[category] = 'welcome-illustration.png'

    category_services_dict = {}
    for category in unique_categories:
        category_services = Service.query.filter_by(category=category).all()  # Get all services for the category
        category_services_dict[category] = category_services

    if not session.get('name'):
        return render_template('index.html', dict_category_path=dict_category_path)        
    
    if session.get('role') == 'customer':
        customer = Customer.query.get_or_404(session.get('customer_id'))
        return render_template('user-view.html', customer=customer, category_services_dict=category_services_dict)
    
    if session.get('role') == 'professional':
        return redirect(url_for('my_service_requests'))
 

@app.route('/customer/signup', methods=['GET', 'POST'])
def custSignup():
    if request.method == 'GET':
        return render_template('customer-signup.html')
    if request.method == 'POST':
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        phone_num = request.form.get("phone_num")
        area = request.form.get("area")
        
        existing_user = Customer.query.filter((Customer.email == email)).first()
        if existing_user:
            flash('Email already exists! Log in instead.', 'danger')
            return redirect(url_for('login'))

        new_customer = Customer(
            name=name,
            email=email,
            password=password,  # In future, hash the password
            phone_num=phone_num,
            area=area,
            date_joined=func.current_date()
        )

        try:
            db.session.add(new_customer)
            db.session.commit()
            flash('Account created successfully!', 'success')
            flash('You can add profile photo from \'Edit Profile\'','info')
            return redirect(url_for('login'))  # Redirect to the login page
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')

    return render_template('customer-signup.html')  # Render the signup form


@app.route('/professional/signup', methods=['GET', 'POST'])
def profSignup():
    if request.method == 'GET':
        services = Service.query.all()
        return render_template('professional-signup.html', services=services)
    
    
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        phone_num = request.form.get("phone_num")
        area = request.form.get("area")
        service = request.form.get("service")
        professional_ask = request.form.get("professionalAsk")
        experience = request.form.get("experience")
        
        document = request.files['document']
        profile_pic = request.files['profile_pic']
        
        filename_doc, filename_pic = None, None
        
        if document and allowed_docs(document.filename):
            filename_doc = secure_filename(document.filename)
            document.save(os.path.join(app.config['PROFESSIONAL_DOCS'], filename_doc))

        if profile_pic and allowed_file(profile_pic.filename):
            filename_pic = secure_filename(profile_pic.filename)
            profile_pic.save(os.path.join(app.config['PROFESSIONAL_PROFILE_PICS'], filename_pic))
        
        service_ = Service.query.get(service)
        if service_.base_price > int(professional_ask):
            flash(f'Base Price for { service_.name } is { service_.base_price}. Your desired charges should be equal or above that value.','danger')
            return render_template('professional-signup.html', services=Service.query.all(), name=name, email=email, phone_num=phone_num, area=area, service=service, professional_ask=professional_ask, experience=experience)
        
        existing_professional = Professional.query.filter((Professional.email == email)).first()
        if existing_professional:
            flash('Email already exists!', 'danger')
            return render_template('professional-signup.html', services=Service.query.all(), name=name, email=email, phone_num=phone_num, area=area, service=service, professional_ask=professional_ask, experience=experience)
        
        new_professional = Professional(
            name=name,
            email=email,
            password=password,  # In future, hash the password
            phone_num=phone_num,
            area=area,
            service_provided = service,
            professional_ask=professional_ask,
            experience = experience,
            created_at=func.current_date(),
            rating=0,
            doc_path=filename_doc,
            profile_pic=filename_pic
        )
        
        try:
            db.session.add(new_professional)
            db.session.commit()
            flash('Professional account created successfully!', 'success')
            flash('You can add profile photo from \'Edit Profile\'','info')
            return redirect(url_for('login'))  # Redirect to the login page
        except Exception as e:
            db.session.rollback()
            flash(f'Error: Something went wrong! Check logs', 'danger')
            print(str(e))

    return render_template('professional-signup.html', services=Service.query.all())  # Render the signup form


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    email = request.form.get('email', None)
    password = request.form.get('password', None)

    if not email:
        flash('Email is required', "danger")
        return redirect(url_for('login'))

    if not password:
        flash('Password is required', "danger")
        return redirect(url_for('login'))

    customer = Customer.query.filter_by(email=email).first()
    if customer:
        if customer.password == password:
            session['name'] = customer.name
            session['customer_id'] = customer.id 
            session['role'] = 'customer'
            if customer.profile_pic:
                session['profile_pic'] = customer.profile_pic
            flash("Login Successful", "success")
            return redirect(url_for('home'))
        else:
            flash('Invalid Password', "danger")
            return redirect(url_for('login'))

    professional = Professional.query.filter_by(email=email).first()
    if professional:
        if professional.password == password:
            session['name'] = professional.name
            session['professional_id'] = professional.id
            session['role'] = 'professional'
            if professional.profile_pic:
                session['profile_pic'] = professional.profile_pic
                # print(professional.profile_pic)
            flash("Login Successful", "success")
            return redirect(url_for('home'))
        else:
            flash('Invalid Password', "danger")
            return redirect(url_for('login'))

    admin = Admin.query.filter_by(email=email).first()
    if admin:
        if admin.password == password:
            session['name'] = admin.name
            session['role'] = 'admin'
            flash("Login Successful", "success")
            return redirect(url_for('admin'))
        else:
            flash('Invalid Password', "danger")
            return redirect(url_for('login'))

    # If no user is found in any table
    flash('Invalid email', "danger")
    return redirect(url_for('login'))

        
@app.route('/logout')
def logout():
    session.pop('name', None)
    session.pop('role', None)
    session.pop('profile_pic', None)
    return redirect(url_for('home'))
            
@app.route('/admin')
def admin():
    if session.get('role') != 'admin':
            flash("You are not authorized. Redirected to main site.", "danger")
            return redirect(url_for('home'))
    if session.get('role') == 'admin':
        services = Service.query.all()
        # print(services)
        professionals = Professional.query.order_by(desc(Professional.id)).all()
        # print(professionals)
        service_requests = ServiceRequest.query.order_by(desc(ServiceRequest.service_request_id)).all()
        return render_template('admin.html', services=services,professionals=professionals, service_requests=service_requests)
    else:
        flash("You are not authorized", "danger")
        return redirect(url_for('home'))
    
@app.route('/admin/add_service', methods=['GET', 'POST'])
def add_service():
    if request.method == 'GET':
        if session.get('role') != 'admin':
            flash("You are not authorized to add services", "danger")
            return redirect(url_for('admin'))
        
        return render_template('add-service.html')
    
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        base_price = request.form.get('base_price')
        description = request.form.get('description')
        
        if 'image' not in request.files:
            flash('No file part', 'danger')
            return redirect(url_for('admin'))
        
        file = request.files['image']
        
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(url_for('admin'))
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash(f'Image {filename} uploaded successfully!', 'success')
        
        new_service = Service(
            name=name, 
            category=category, 
            base_price=base_price, 
            description=description,
            image=filename)
        
        db.session.add(new_service)
        db.session.commit()

        flash('Service added successfully!', 'success')
        return admin()
    
@app.route('/admin/update_service/<int:service_id>', methods=['GET', 'POST'])
def update_service(service_id):
    service = Service.query.get_or_404(service_id)
    
    if request.method == 'GET':
        return render_template('update_service.html', service=service)

    if request.method == 'POST':
        service.name = request.form.get('name')
        service.category = request.form.get('category')
        service.base_price = request.form.get('base_price')
        service.description = request.form.get('description')
        
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                if service.image:
                    old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], service.image)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)

                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                service.image = filename
                flash(f'Image {filename} uploaded successfully!', 'success')

        db.session.commit()
        flash('Service updated successfully!', 'success')
        return redirect(url_for('admin'))


@app.route('/admin/delete_service/<int:service_id>', methods=['POST'])
def delete_service(service_id):
    service = Service.query.get_or_404(service_id)
    
    if service.image:
        image_path = os.path.join(app.root_path, 'static/', service.image)
        if os.path.exists(image_path):
            os.remove(image_path)

    db.session.delete(service)
    db.session.commit()
    
    flash('Service deleted successfully!', 'success')
    return redirect(url_for('admin'))
        
@app.route('/admin/approve_prof/<int:prof_id>', methods=['GET'])
def approve_prof(prof_id):
    professional = Professional.query.get_or_404(prof_id)
    professional.approval_status = True
    db.session.commit()
    flash(f'{professional.name.capitalize()}\'s approval accepted', 'success')
    return redirect(url_for('admin'))
    
@app.route('/admin/reject_prof/<int:prof_id>', methods=['GET'])
def reject_prof(prof_id):
    professional = Professional.query.get_or_404(prof_id)
    professional.approval_status = False
    db.session.commit()
    flash(f'{professional.name.capitalize()}\'s approval denied', 'success')
    
    return redirect(url_for('admin'))

@app.route('/admin/delete_prof/<int:prof_id>', methods=['GET'])
def delete_prof(prof_id):
    professional = Professional.query.get_or_404(prof_id)
    
    if professional.profile_pic:
        profile_pic_path = os.path.join(app.root_path, 'static/prof-profile-pics', professional.profile_pic)
        if os.path.exists(profile_pic_path):
            os.remove(profile_pic_path)

    if professional.doc_path:
        doc_path = os.path.join(app.root_path, 'static/prof-docs', professional.doc_path)
        if os.path.exists(doc_path):
            os.remove(doc_path)

    db.session.delete(professional)
    db.session.commit()

    flash(f'Professional {professional.name.capitalize()} deleted successfully, along with their files!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/documents/<filename>')
def download_document(filename):
    return send_from_directory(app.config['PROFESSIONAL_DOCS'], filename)

@app.route('/admin/profile-pic/<filename>')
def download_profile_pic(filename):
    return send_from_directory(app.config['PROFESSIONAL_PROFILE_PICS'], filename)

@app.route('/admin/service-pic/<filename>')
def download_service_pic(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/admin/reject_customer/<int:cust_id>', methods=['GET'])
def flag_customer(cust_id):
    customer = Customer.query.get_or_404(cust_id)
    
    customer.flag = True
    
    db.session.commit()
    flash(f'Customer {customer.name.capitalize()} flagged successfully', 'success')
    return redirect(url_for('search'))
       
@app.route('/admin/approve_customer/<int:cust_id>', methods=['GET'])
def unflag_customer(cust_id):
    customer = Customer.query.get_or_404(cust_id)
    
    customer.flag = False
    
    db.session.commit()
    flash(f'Customer {customer.name.capitalize()} unflagged successfully', 'success')
    return redirect(url_for('search'))
    
@app.route('/admin/delete_customer/<int:cust_id>', methods=['GET'])
def delete_customer(cust_id):
    customer = Customer.query.get_or_404(cust_id)
    
    if customer.profile_pic:
        profile_pic_path = os.path.join(app.root_path, 'static/cust-profile-pics', customer.profile_pic)
        if os.path.exists(profile_pic_path):
            os.remove(profile_pic_path)
            
    db.session.delete(customer)
    db.session.commit()
    flash(f"Customer { customer.name.capitalize() } removed from database", 'success')
    return redirect(url_for('admin'))    
    

@app.route('/service/<int:service_id>', methods=["GET", "POST"])
def request_service(service_id):
    if request.method == "GET":
        service = Service.query.get_or_404(service_id)
        customer = Customer.query.get_or_404(session['customer_id'])
        
        # professionals who provide this service
        professionals = Professional.query.filter_by(approval_status=True).filter_by(service_provided=service.service_id).filter_by(area=customer.area).all()
        
        return render_template('request-service.html', service=service, professionals=professionals)

    if request.method == "POST":
        selected_professional_id = request.form.get('professional_id')
        
        if not selected_professional_id:
            flash("Please select a professional.", 'danger')
            return redirect(url_for('request_service', service_id=service_id))

        service = Service.query.get_or_404(service_id)

        date_for_request_str = request.form.get('date_for_request')
        try:
            date_for_request = datetime.strptime(date_for_request_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", 'danger')
            return redirect(url_for('request_service', service_id=service_id))

        requested_by = session.get('customer_id')
        if not requested_by:
            flash("You must be logged in to make a service request.", 'danger')
            return redirect(url_for('login'))

        status = 'requested'  # default

        new_service_request = ServiceRequest(
            requested_by=requested_by,
            requested_for=selected_professional_id,
            status=status,
            service_id=service.service_id,
            date_for_request=date_for_request
        )

        try:
            db.session.add(new_service_request)
            db.session.commit()
            professional = Professional.query.get_or_404(selected_professional_id)
            
            flash(f"Service request made to {professional.name.capitalize()} successfully! You can check the status of your requests in \"My Service Requests\"", 'success')
            return redirect(url_for('home'))

        except IntegrityError:
            db.session.rollback()
            flash("An error occurred while creating the service request. Please try again.", 'danger')
            return redirect(url_for('request_service', service_id=service_id))
        except Exception as e:
            db.session.rollback()
            flash(f"An unexpected error occurred: {str(e)}", 'danger')
            return redirect(url_for('home'))


@app.route('/my-service-requests')
def my_service_requests():
    if session.get('role') == 'customer':
        customer_id = session.get('customer_id')
        service_requests = ServiceRequest.query.filter(
            ServiceRequest.requested_by == customer_id,
            ServiceRequest.status != "closed"
            ).all()
        
        closed_service_requests = ServiceRequest.query.filter(
            ServiceRequest.requested_by == customer_id,
            ServiceRequest.status == "closed",
        ).all()
        return render_template('my-service-requests.html', service_requests=service_requests, closed_service_requests=closed_service_requests)
    
    elif session.get('role') == 'professional':
        professional_id = session.get('professional_id')
        professional = Professional.query.get(professional_id)
        
        service_requests = ServiceRequest.query.filter(
            ServiceRequest.requested_for == professional_id,
            ServiceRequest.status != "rejected",
            ServiceRequest.status != "closed",
        ).all()
        
        closed_service_requests = ServiceRequest.query.filter(
            ServiceRequest.requested_for == professional_id,
            ServiceRequest.status == "closed",
        ).order_by(ServiceRequest.service_request_id.desc()).all()
        
        return render_template('my-service-requests.html', service_requests=service_requests, professional=professional, closed_service_requests=closed_service_requests)
    
    else:
        flash("You must be logged in to view your service requests.", 'danger')
        return redirect(url_for('login'))


@app.route('/update_service_request/<int:service_request_id>', methods=["GET", "POST"])
def update_service_request(service_request_id):
    service_request = ServiceRequest.query.get_or_404(service_request_id)
    if session.get('role') == "customer" and service_request.status != "completed":
        current_user_id = session.get('customer_id')
        if service_request.requested_by != current_user_id:
            flash("You are not authorized to update this service request.", 'danger')
            return redirect(url_for('my_service_requests'))

        if request.method == "GET":
            return render_template("update-service-request.html", service_request=service_request)

        if request.method == "POST":
            date_for_request_str = request.form.get("date_for_request") 

            try:
                date_for_request = datetime.strptime(date_for_request_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD.", 'danger')
                return redirect(url_for('update_service_request', service_request_id=service_request_id))

            service_request.date_for_request = date_for_request 
            service_request.status = "requested"

            try:
                db.session.commit()
                flash("Service request updated successfully!", 'success')
                return redirect(url_for('my_service_requests'))
            except Exception as e:
                db.session.rollback()
                flash(f"An error occurred while updating the service request: {str(e)}", 'danger')
                return redirect(url_for('update_service_request', service_request_id=service_request_id))


    if session.get('role') == "customer" and service_request.status == "completed":
        if request.method == "GET":
            return render_template("update-service-request.html", service_request=service_request)

        if request.method == "POST":
            service_rating = request.form.get("service_rating") 
            remarks = request.form.get("remarks")

            service_request.service_rating = service_rating
            service_request.remarks = remarks
            service_request.status = "closed"
            service_request.date_of_completion = func.current_date()

            professional = service_request.professional
            all_ratings = [int(req.service_rating) for req in professional.service_requests if req.service_rating is not None]

            all_ratings.append(float(service_rating))
                        
            average_rating = sum(all_ratings) / len(all_ratings)

            professional.rating = round(average_rating, 2)  # rating rounded to 2 decimal places

            db.session.commit()

            flash(f"Rating and Remark added and Service Status set to 'Closed'!", "success")
            return redirect(url_for('my_service_requests'))

        
    if session.get('role') == 'professional':
        current_user_id = session.get('professional_id')
        if service_request.requested_for == current_user_id:
            if request.method == "GET":
                return render_template("update-service-request.html", service_request=service_request)
            
            if request.method == "POST":
                customer_rating = request.form.get('customer_rating')
                
                service_request.customer_rating = customer_rating
                
                customer = service_request.customer
                
                all_ratings = []
                for req in customer.service_requests:
                    if req.customer_rating is not None:
                        all_ratings.append(int(req.customer_rating))
                
                # all_ratings.append(int(customer_rating))
                
                # print(all_ratings)
                # print(all_ratings)
                # print(all_ratings)
                # print(all_ratings)
                # print(all_ratings)
                
                average_rating = sum(all_ratings) / len(all_ratings)
                # print(average_rating)
                
                customer.rating = round(average_rating, 2)
                # print(round(average_rating, 2))
                
                db.session.commit()
                

                flash(f"Customer Rating updated!", "success")
                return redirect(url_for('my_service_requests')) 

        if service_request.requested_for != current_user_id:
            flash("You are not authorized to update this service request.", 'danger')
            return redirect(url_for('my_service_requests'))
            


@app.route('/acc_service_request/<int:service_request_id>')   
def accept_service_request(service_request_id):
    service_request = ServiceRequest.query.get_or_404(service_request_id)
    if service_request.status == 'requested':
        service_request.status = "accepted"
        db.session.commit()
        flash(f"Service request for {service_request.service.name} and id {service_request.service_request_id} accepted.", "success")
        return redirect(url_for('my_service_requests'))
    elif service_request.status == 'accepted':
        service_request.status = "completed"
        db.session.commit()
        flash(f"Service request for {service_request.service.name} and id {service_request.service_request_id} completed.", "success")
        return redirect(url_for('my_service_requests'))
    else:
        flash(f"Service was already accepted.", "danger")
        return redirect(url_for('my_service_requests'))
        

@app.route('/rej_service_request/<int:service_request_id>')   
def reject_service_request(service_request_id):
    service_request = ServiceRequest.query.get_or_404(service_request_id)
    if service_request.status == 'requested' or service_request.status == 'accepted':
        service_request.status = "rejected"
        db.session.commit()
        flash(f"Service request for {service_request.service.name} and id {service_request.service_request_id} rejected.", "danger")
        return redirect(url_for('my_service_requests'))
    

@app.route('/del_service_request/<int:service_request_id>', methods=["POST"])
def delete_service_request(service_request_id):
     # yahaan pe check if the correct user is accessing the url.
    service_request = ServiceRequest.query.get_or_404(service_request_id)
    temp_name = service_request.service.name
    db.session.delete(service_request)
    db.session.commit()
    flash(f'Service Request for {temp_name.capitalize()} deleted successfully!', 'success')
    
    return redirect(url_for('my_service_requests'))


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    filter_type = request.args.get('filter')
    user_role = session.get('role') 
    results = None
        
    if user_role == 'admin':
        if filter_type == 'service_request':
            results = ServiceRequest.query.filter(
    or_(
        ServiceRequest.service_request_id.ilike(f"{query}"),
        ServiceRequest.status.ilike(f"%{query}%"),
        ServiceRequest.professional.has(Professional.name.ilike(f"%{query}%")),
        ServiceRequest.customer.has(Customer.name.ilike(f"%{query}%")),
        ServiceRequest.date_for_request.ilike(f"%{query}%"),
        ServiceRequest.date_of_request.ilike(f"%{query}%"),
        ServiceRequest.date_of_completion.ilike(f"%{query}%") 
             
        )).all()
            
        elif filter_type == 'services':
            results = Service.query.filter(
    or_(
        Service.service_id.ilike(f"{query}"),
        Service.name.ilike(f"%{query}%"),
        Service.description.ilike(f"%{query}%"),
        Service.base_price.ilike(f"%{query}%"),
        Service.category.ilike(f"%{query}%"),
    )).all()
            
        elif filter_type == 'customers':
            results = Customer.query.filter(
    or_(
        Customer.name.ilike(f"%{query}%"),
        Customer.area.ilike(f"%{query}%"),
        Customer.email.ilike(f"%{query}%"),
        Customer.phone_num.ilike(f"%{query}%"),
        Customer.flag.ilike(f"%{query}%"),
    )).all() 
    
        elif filter_type == "professionals":
            results = Professional.query.join(Service, Service.service_id == Professional.service_provided).filter(
                or_(
                    Professional.name.ilike(f"%{query}%"),
                    Professional.email.ilike(f"%{query}%"),
                    Professional.phone_num.ilike(f"%{query}%"),
                    Professional.area.ilike(f"%{query}%"),
                    Service.name.ilike(f"%{query}%"),
                    Professional.approval_status.ilike(f"%{query}%"),
                    Professional.professional_ask.ilike(f"%{query}%"),
                    Professional.experience.ilike(f"%{query}%"),
                    Professional.rating.ilike(f"%{query}%")
                )
            ).all() 
            return render_template('search.html', results=results)
            
        return render_template('search.html', results=results)
    
    if user_role == 'professional':
        if filter_type == 'service_request':
            results = ServiceRequest.query.filter(
            ServiceRequest.requested_for == session.get('professional_id'),
            or_(
                ServiceRequest.service_request_id.ilike(f"{query}"),
                ServiceRequest.status.ilike(f"%{query}%"),
                ServiceRequest.professional.has(Professional.name.ilike(f"%{query}%")),
                ServiceRequest.customer.has(Customer.name.ilike(f"%{query}%")),
                ServiceRequest.date_for_request.ilike(f"%{query}%"),
                ServiceRequest.date_of_request.ilike(f"%{query}%"),
                ServiceRequest.date_of_completion.ilike(f"%{query}%") 
            )
        ).all() 

        return render_template('search.html', results=results)
    
    if user_role == 'customer':
        # if something
        if filter_type == 'service_request':
            results = ServiceRequest.query.filter(
                ServiceRequest.requested_for == session.get('customer_id'),
                or_(
                    ServiceRequest.service_request_id.ilike(f"{query}"),
                    ServiceRequest.status.ilike(f"%{query}"),
                    ServiceRequest.customer.has(Customer.name.ilike(f"%{query}%")),
                    ServiceRequest.professional.has(Professional.name.ilike(f"%{query}%")),
                    ServiceRequest.date_for_request.ilike(f"%{query}%"),
                    ServiceRequest.date_of_request.ilike(f"%{query}%"),
                    ServiceRequest.date_of_completion.ilike(f"%{query}%") 
                )
            ).all()
        elif filter_type == "services":
            results = Service.query.filter(
                or_(
                    Service.service_id.ilike(f"{query}"),
                    Service.name.ilike(f"%{query}%"),
                    Service.description.ilike(f"%{query}%"),
                    Service.base_price.ilike(f"%{query}%"),
                    Service.category.ilike(f"%{query}%"),
                )).all()
        
        elif filter_type == "professionals":
            results = Professional.query.join(Service, Service.service_id == Professional.service_provided).filter(
                or_(
                    Professional.name.ilike(f"%{query}%"),
                    Professional.email.ilike(f"%{query}%"),
                    Professional.phone_num.ilike(f"%{query}%"),
                    Professional.area.ilike(f"%{query}%"),
                    Service.name.ilike(f"%{query}%"),
                    Professional.approval_status.ilike(f"%{query}%"),
                    Professional.professional_ask.ilike(f"%{query}%"),
                    Professional.experience.ilike(f"%{query}%"),
                    Professional.rating.ilike(f"%{query}%")
                )
            ).all()
        
        return render_template('search.html', results=results)   
    

@app.route('/edit-profile', methods=['GET','POST'])
def edit_profile():
    if session.get('role') == "customer":
        if request.method == 'GET':
            customer = Customer.query.get(session.get('customer_id'))
            return render_template("edit-profile.html", customer=customer)

        if request.method == "POST":
            customer = Customer.query.get(session.get('customer_id'))

            # Update fields only if they are non-empty
            customer.name = request.form.get('name') or customer.name
            session['name'] = request.form.get('name') or session.get('name')
        
            customer.email = request.form.get('email') or customer.email
            customer.password = request.form.get('password') or customer.password
            customer.phone_num = request.form.get('phone_num') or customer.phone_num
            customer.area = request.form.get('area') or customer.area

            file = request.files.get('image')
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                
                if customer.profile_pic:
                    old_file_path = os.path.join(app.config['PROFILE_PIC_FOLDER'], customer.profile_pic)
                    
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                        flash(f'Old profile picture {customer.profile_pic} deleted!', 'info')

                file.save(os.path.join(app.config['PROFILE_PIC_FOLDER'], filename))
                flash(f'Image {filename} uploaded successfully!', 'success')

                customer.profile_pic = filename
                session['profile_pic'] = filename

            db.session.commit()
            flash(f"Profile Updated!", "success")
            return redirect(url_for('home'))
        
    if session.get('role') == "professional":
        if request.method == 'GET':
            professional = Professional.query.get(session.get('professional_id'))
            services = Service.query.all()
            return render_template("edit-profile.html", professional=professional, services=services)
        if request.method == "POST":
            professional = Professional.query.get(session.get('professional_id'))
            
            professional.name = request.form.get('name') or professional.name
            session['name'] = request.form.get('name') or session.get('name')
            professional.email = request.form.get('email') or professional.email
            professional.password = request.form.get('password') or professional.password
            professional.phone_num = request.form.get('phone_num') or professional.phone_num
            professional.area = request.form.get('area') or professional.area
            professional.service_provided = request.form.get('service') or professional.service_provided
            professional.professional_ask = request.form.get('professionalAsk') or professional.professional_ask
            professional.experience = request.form.get('experience') or professional.experience

            file = request.files.get('image')
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                
                if professional.profile_pic:
                    old_file_path = os.path.join(app.config['PROFESSIONAL_PROFILE_PICS'], professional.profile_pic)
                    
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                        flash(f'Old profile picture {professional.profile_pic} deleted!', 'info')

                file.save(os.path.join(app.config['PROFESSIONAL_PROFILE_PICS'], filename))
                flash(f'Image {filename} uploaded successfully!', 'success')

                professional.profile_pic = filename
                session['profile_pic'] = filename
            
            professional.approval_status = False

            db.session.commit()
            flash(f"Profile Updated! Waiting for approval from admin.", "success")
            return redirect(url_for('home'))
        



def generate_nested_data():
    # Step 1: Query ratings and services
    # Group by `service_rating` and `service_id`, count occurrences
    query_results = (
        ServiceRequest.query
        .join(Service, ServiceRequest.service_id == Service.service_id)
        .with_entities(
            ServiceRequest.service_rating,
            Service.name,
            func.count(ServiceRequest.service_request_id).label("count")
        )
        .group_by(ServiceRequest.service_rating, Service.service_id)
        .order_by(ServiceRequest.service_rating)
        .all()
    )

    # Step 2: Organize results into the nested structure
    data = {"name": "Ratings", "children": []}
    rating_dict = {}

    for rating, service_name, count in query_results:
        rating_label = f"Rating: {int(rating)}" if rating is not None else "Unrated"
        
        # Create a nested dictionary for each rating if not already created
        if rating_label not in rating_dict:
            rating_dict[rating_label] = {"name": rating_label, "children": []}
        
        # Add service data to the rating
        rating_dict[rating_label]["children"].append({"name": service_name, "value": count})
    
    # Convert dictionary to list format
    data["children"] = list(rating_dict.values())
    
    return data

def data_for_admin2():
    service_requests_by_date = (
    ServiceRequest.query
    .with_entities(ServiceRequest.date_of_request, func.count(ServiceRequest.service_request_id).label("request_count"))
    .group_by(ServiceRequest.date_of_request)
    .order_by(ServiceRequest.date_of_request)
    .all()
)
    data = [[date.strftime("%Y-%m-%d"), count] for date, count in service_requests_by_date]
    # print(data)
    return data

def data_for_admin3():
    # Initialize the dictionary with all statuses and count 0
    status_counts = {
        "requested": 0,
        "accepted": 0,
        "rejected": 0,
        "closed": 0
    }

    # Query to count service requests by status
    service_requests_by_status = (
        ServiceRequest.query
        .with_entities(ServiceRequest.status, func.count(ServiceRequest.service_request_id).label("request_count"))
        .group_by(ServiceRequest.status)
        .all()
    )

    # Update the dictionary with actual counts from the database
    for status, count in service_requests_by_status:
        status_counts[status] = count

    # Convert the dictionary to a list of lists for JavaScript
    data = [[status, count] for status, count in status_counts.items()]
    
    # print(data)
    return data

def data_for_admin4():
    service_requests_by_area = (
    ServiceRequest.query
    .join(Professional, ServiceRequest.requested_for == Professional.id)
    .with_entities(Professional.area, func.count(ServiceRequest.service_request_id).label("request_count"))
    .group_by(Professional.area)
    .all()
)
    data = [[area, count] for area, count in service_requests_by_area]
    print(data)
    return data
    
def data_for_admin5():
    service_requests_by_service = (
    ServiceRequest.query
    .join(Service, ServiceRequest.service_id == Service.service_id)
    .with_entities(Service.name, func.count(ServiceRequest.service_request_id).label("request_count"))
    .group_by(Service.name)
    .order_by(func.count(ServiceRequest.service_request_id).desc())
    .all()
)

    data = [[service_name, count] for service_name, count in service_requests_by_service]
    return data
 
def data_for_professional1():
    professional_id = session.get('professional_id')
    ratings_data = (
    ServiceRequest.query
    .filter(ServiceRequest.requested_for == professional_id)
    .with_entities(ServiceRequest.service_rating, func.count(ServiceRequest.service_rating).label("rating_count"))
    .group_by(ServiceRequest.service_rating)
    .order_by(ServiceRequest.service_rating)
    .all()
)
    # Format data for JavaScript
    data = [[rating, count] for rating, count in ratings_data]
    
    return data
    
def data_for_professional2():
        professional_id = session.get('professional_id')
        closed_requests_data = (
            ServiceRequest.query
            .filter(ServiceRequest.requested_for == professional_id, ServiceRequest.status == 'closed')
            .with_entities(ServiceRequest.date_of_completion, func.count(ServiceRequest.service_request_id).label("request_count"))
            .group_by(ServiceRequest.date_of_completion)
            .order_by(ServiceRequest.date_of_completion)
            .all()
        )
        data = [[date.isoformat(), count] for date, count in closed_requests_data]
        return data

def data_for_professional3():
    professional_id = session.get('professional_id')

    # Initialize the dictionary with all statuses and count 0
    status_counts = {
        "requested": 0,
        "accepted": 0,
        "rejected": 0,
        "closed": 0
    }

    # Query to count service requests by status for the specific professional
    status_data = (
        ServiceRequest.query
        .filter(ServiceRequest.requested_for == professional_id)
        .with_entities(ServiceRequest.status, func.count(ServiceRequest.service_request_id).label("request_count"))
        .group_by(ServiceRequest.status)
        .all()
    )

    # Update the dictionary with actual counts from the database
    for status, count in status_data:
        status_counts[status] = count

    # Convert the dictionary to a list of lists for JavaScript
    data = [[status, count] for status, count in status_counts.items()]

    return data

def data_for_customer1():
    customer_id = session.get('customer_id')
    requests_by_date = (
        ServiceRequest.query
        .filter(ServiceRequest.requested_by == customer_id)
        .with_entities(ServiceRequest.date_of_completion, func.count(ServiceRequest.service_request_id).label("request_count"))
        .group_by(ServiceRequest.date_of_completion)
        .order_by(ServiceRequest.date_of_completion)
        .all()
    )
    data = [[date.isoformat(), count] for date, count in requests_by_date]
    return data

def data_for_customer2():
    customer_id = session.get('customer_id')
    status_counts = {
        "requested": 0,
        "accepted": 0,
        "rejected": 0,
        "closed": 0
    }
    status_data = (
        ServiceRequest.query
        .filter(ServiceRequest.requested_by == customer_id)
        .with_entities(ServiceRequest.status, func.count(ServiceRequest.service_request_id).label("request_count"))
        .group_by(ServiceRequest.status)
        .all()
    )
    for status, count in status_data:
        status_counts[status] = count
    
    data = [[status, count] for status, count in status_counts.items()]
    return data
       
@app.route('/summary', methods=['GET'])
def summary():
    role = session.get('role')
    if role == 'admin':
        data = generate_nested_data()
        data_json = json.dumps(data)
        
        admin_2_data = data_for_admin2()
        admin_2_data_json = json.dumps(admin_2_data)
        
        admin_3_data = data_for_admin3()
        admin_3_data_json = json.dumps(admin_3_data)
        
        admin_4_data = data_for_admin4()
        admin_4_data_json = json.dumps(admin_4_data)
        
        admin_5_data = data_for_admin5()
        admin_5_data_json = json.dumps(admin_5_data)
        
        return render_template('summary_admin.html', data=data_json, admin_2_data=admin_2_data_json, admin_3_data=admin_3_data_json, admin_4_data=admin_4_data_json, admin_5_data=admin_5_data_json)
    
    if role == 'professional':
        professional_1_data = data_for_professional1()
        professional_1_data_json = json.dumps(professional_1_data)
        
        professional_2_data = data_for_professional2()
        professional_2_data_json = json.dumps(professional_2_data)
        
        professional_3_data = data_for_professional3()
        professional_3_data_json = json.dumps(professional_3_data)
        
        return render_template('summary_prof.html', professional_1_data=professional_1_data_json, professional_2_data=professional_2_data_json, professional_3_data=professional_3_data_json)
    
    if role == 'customer':
        customer_1_data = data_for_customer1()
        customer_1_data_json = json.dumps(customer_1_data)
        
        customer_2_data = data_for_customer2()
        customer_2_data_json = json.dumps(customer_2_data)
        
        return render_template('summary_cust.html', customer_1_data=customer_1_data_json, customer_2_data=customer_2_data_json)
            
            
            

            


            

            
            
            
    
      





# @app.route('/delete_specific_professionals', methods=["GET"])
# def delete_specific_professionals():
#     # Perform the delete operation for specific professionals
#     try:
#         # Define the names of professionals you want to delete
#         names_to_delete = ['nimish', 'saket', 'bai', 'Tony Stark']
        
#         # Query and delete professionals whose names match the list
#         db.session.query(Professional).filter(Professional.name.in_(names_to_delete)).delete(synchronize_session=False)
#         db.session.commit()

#         flash('Selected professionals have been successfully deleted.', 'success')
#     except Exception as e:
#         db.session.rollback()  # In case of error, rollback the transaction
#         flash(f'Error deleting professionals: {str(e)}', 'danger')
    
#     return redirect(url_for('my_service_requests'))

    
