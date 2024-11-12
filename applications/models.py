from applications.database import db
from sqlalchemy import func


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False) 
    password = db.Column(db.String(15), nullable=False) # in future hash it and then store it
    
    phone_num = db.Column(db.String(10), nullable=False) # figure out the correct format for phone nums?
    area = db.Column(db.String(50), nullable=False)
    
    date_joined = db.Column(db.Date, default=func.current_date())
    profile_pic = db.Column(db.String(250), nullable=True)
    
    flag = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float, nullable=True)
    
    # regex?? email etc. verification // something analogous to zod
    # add relations
    
class Professional(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False) 
    password = db.Column(db.String(15), nullable=False) # in future hash it and then store it
    
    phone_num = db.Column(db.String(10), nullable=False) # figure out the correct format for phone nums?
    area = db.Column(db.String(50), nullable=False)
    
    created_at = db.Column(db.Date, default=func.current_date())
    updated_at = db.Column(db.Date, default=func.current_date())
    
    profile_pic = db.Column(db.String(250), nullable=False, default="")
    
    approval_status = db.Column(db.Boolean, default=False, nullable=False)

    service_provided = db.Column(db.Integer, db.ForeignKey('service.service_id'), nullable=False)
    service = db.relationship('Service', backref='professionals', lazy=True)

    professional_ask = db.Column(db.Integer, nullable=True)
    experience = db.Column(db.Integer, nullable=False)
    rating = db.Column(db.Float, nullable=True) 

    doc_path = db.Column(db.String(250), nullable=False, default="")
    
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False) 
    password = db.Column(db.String(15), nullable=False) # in future hash it and then store it
    
    date_joined = db.Column(db.Date, default=func.current_date())
    profile_pic = db.Column(db.String(250), nullable=True)


class Service(db.Model):    
    service_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category = db.Column(db.String(10))
    base_price = db.Column(db.Float, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(250), nullable=True)
    image = db.Column(db.String(100), nullable=True)
    
    service_requests = db.relationship('ServiceRequest', backref='service', lazy=True, cascade="all, delete-orphan")

class ServiceRequest(db.Model):
    service_request_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    requested_by = db.Column(db.Integer, db.ForeignKey('customer.id', name="fk_service_request_requested_by_customer_id", ondelete='SET NULL'),nullable=True)
    requested_for = db.Column(db.Integer, db.ForeignKey('professional.id', name="fk_service_request_requested_for_professional_id", ondelete='SET NULL'), nullable=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.service_id', name='fk_service_request_service', ondelete='CASCADE'), nullable=False)

    customer = db.relationship('Customer', backref='service_requests', lazy=True)  # Relationship to Customer
    professional = db.relationship('Professional', backref='service_requests', lazy=True)  # Relationship to Professional

    status = db.Column(db.String(20), nullable=False, default='requested')  # e.g., requested, accepted, rejected, closed
    service_rating = db.Column(db.Float, nullable=True)
    customer_rating = db.Column(db.Float, nullable=True)
    remarks = db.Column(db.String(250), nullable=True)

    date_of_request = db.Column(db.Date, default=func.current_date())
    date_for_request = db.Column(db.Date)
    date_of_completion = db.Column(db.Date, nullable=True)