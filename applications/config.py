class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/'
    PROFILE_PIC_FOLDER = 'static/cust-profile-pics/'
    PROFESSIONAL_PROFILE_PICS = 'static/prof-profile-pics/'
    PROFESSIONAL_DOCS = 'static/prof-docs'

    SECRET_KEY = 'myprojectsecretkey'