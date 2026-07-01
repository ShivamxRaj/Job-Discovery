import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

async def send_verification_email(email: str, token: str):
    """Send verification email link via SMTP"""
    if not (settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD):
        print(f"[SMTP NOT CONFIG] Verification Email token: {token}")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        msg['To'] = email
        msg['Subject'] = "Verify your JobDiscovery AI Account"
        
        verification_link = f"http://localhost:3000/verify-email?token={token}"
        
        html = f"""
        <html>
            <body>
                <h3>Welcome to JobDiscovery AI!</h3>
                <p>Please click the link below to verify your email address and complete registration:</p>
                <p><a href="{verification_link}">{verification_link}</a></p>
                <br/>
                <p>This verification link will expire in 24 hours.</p>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.EMAILS_FROM_EMAIL, email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send verification email to {email}: {e}")
        return False

async def send_reset_password_email(email: str, token: str):
    """Send password reset email link via SMTP"""
    if not (settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD):
        print(f"[SMTP NOT CONFIG] Password Reset Email token: {token}")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        msg['To'] = email
        msg['Subject'] = "Reset your JobDiscovery AI Password"
        
        reset_link = f"http://localhost:3000/reset-password?token={token}"
        
        html = f"""
        <html>
            <body>
                <h3>Password Reset Request</h3>
                <p>We received a request to reset your password. Click the link below to choose a new password:</p>
                <p><a href="{reset_link}">{reset_link}</a></p>
                <br/>
                <p>This password reset link will expire in 1 hour. If you did not make this request, you can safely ignore this email.</p>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.EMAILS_FROM_EMAIL, email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send password reset email to {email}: {e}")
        return False
