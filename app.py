from flask import Flask, render_template, session
from applications.database import db
from applications.config import Config
from applications.models import *
from flask_migrate import Migrate


def create_app():
    app = Flask(__name__, template_folder='template')
    app.config.from_object(Config)

    
    db.init_app(app)
    migrate = Migrate(app,db,render_as_batch=True)

    with app.app_context():
        db.create_all()
        
        admin = Admin.query.filter_by(name='admin').first()
        if not admin:
            admin = Admin(name='admin',
                         email = 'admin@abc.com',
                        password = 'admin'
                        )
            db.session.add(admin)

        db.session.commit()
    
    return app

app = create_app()

from applications.routes import *

# @app.route('/professional/login')

if __name__ == '__main__':
    app.run(debug=True)