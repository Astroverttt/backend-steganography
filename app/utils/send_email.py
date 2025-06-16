from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from app.core.config import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,   
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,     
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

env = Environment(loader=FileSystemLoader("app/templates"))

async def send_certificate_email(to_email: EmailStr, context: dict):
    try:
        template = env.get_template("certificate_email.html")
        html_content = template.render(**context)
    except TemplateNotFound:
        raise RuntimeError("Template 'certificate_email.html' not found in app/templates")

    message = MessageSchema(
        subject="Sertifikat Kepemilikan Karya Digital",
        recipients=[to_email],
        body=html_content,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)
