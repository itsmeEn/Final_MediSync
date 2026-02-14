# MediSync Admin Dashboard

A separate admin dashboard for managing user verification requests in the MediSync system.

## Features

- **Separate Admin Site**: Completely independent from the main MediSync application
- **User Verification Management**: Accept, decline, archive verification requests
- **Email Notifications**: Automatic email notifications to users
- **Document Viewer**: View uploaded verification documents
- **Search & Filter**: Filter by status and search by name/email
- **Statistics Dashboard**: Real-time statistics on verification statuses
- **Audit Logging**: Track all admin actions for compliance
- **Responsive Design**: Works on desktop and mobile devices

## Setup Instructions

### 1. Backend Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Migrations**:
   ```bash
   python manage.py makemigrations admin_site
   python manage.py migrate
   ```

3. **Create Admin User**:
   ```bash
   python manage.py shell
   ```
   ```python
   from admin_site.models import AdminUser
   admin = AdminUser.objects.create_user(
       email='admin@medisync.com',
       password='admin123456',
       full_name='Admin User',
       is_super_admin=True
   )
   print(f"Admin user created: {admin.email}")
   ```

4. **Start Backend Server**:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

### 2. Frontend Setup

1. **Serve the Admin Frontend**:
   ```bash
   # Using Python's built-in server
   cd admin-frontend
   python -m http.server 8080
   
   # Or using Node.js http-server
   npx http-server -p 8080
   ```

2. **Access the Admin Dashboard**:
   - Open browser and go to: `http://localhost:8080`
   - Login with admin credentials

## API Endpoints

### Authentication
- `POST /api/admin/login/` - Admin login

### Dashboard
- `GET /api/admin/dashboard/stats/` - Get dashboard statistics

### Verification Management
- `GET /api/admin/verifications/` - List all verification requests
- `POST /api/admin/verifications/{id}/accept/` - Accept verification
- `POST /api/admin/verifications/{id}/decline/` - Decline verification
- `POST /api/admin/verifications/{id}/archive/` - Archive verification
- `PUT /api/admin/verifications/{id}/update/` - Update verification details

### System Logs
- `GET /api/admin/logs/` - Get system logs (Super Admin only)

## Usage

### Login
1. Navigate to the admin dashboard
2. Enter admin email and password
3. Click "Sign In"

### Managing Verifications
1. **View All Requests**: See all verification requests in the table
2. **Filter**: Use status filter or search by name/email
3. **Actions**:
   - **Accept**: Approve verification and send email notification
   - **Decline**: Decline with reason and optional email notification
   - **View**: Open document viewer to see uploaded files
   - **Archive**: Archive old verification requests

### Statistics
- View real-time counts of pending, approved, declined, and archived verifications
- Statistics update automatically when actions are performed

## Security Features

- **JWT Authentication**: Secure token-based authentication
- **Role-based Access**: Only admin users can access admin endpoints
- **Audit Logging**: All actions are logged for compliance
- **Input Validation**: Proper validation for all inputs
- **CORS Protection**: Configured CORS for security

## Email Notifications

### Approval Email
```
Subject: Verification Approved - MediSync
Dear [User Name],

Your verification request has been approved! 
You can now access all features of your MediSync account.

Thank you for your patience.

Best regards,
MediSync Admin Team
```

### Decline Email
```
Subject: Verification Declined - MediSync
Dear [User Name],

Your verification request has been declined for the following reason:

[Reason]

Please review the requirements and submit a new verification request 
with the correct documentation.

If you have any questions, please contact our support team.

Best regards,
MediSync Admin Team
```

## Configuration

### Environment Variables
- `DEFAULT_FROM_EMAIL`: Email address for sending notifications
- `EMAIL_HOST`: SMTP server host
- `EMAIL_PORT`: SMTP server port
- `EMAIL_HOST_USER`: SMTP username
- `EMAIL_HOST_PASSWORD`: SMTP password

### API Configuration
- Update `API_BASE_URL` in `admin.js` if backend runs on different port
- Default: `http://localhost:8000/api/admin`

## Troubleshooting

### Common Issues

1. **CORS Errors**:
   - Ensure CORS is properly configured in Django settings
   - Check that admin frontend URL is in `CORS_ALLOWED_ORIGINS`

2. **Authentication Errors**:
   - Verify admin user exists in database
   - Check JWT token expiration
   - Ensure proper email/password combination

3. **Email Notifications Not Sending**:
   - Check email configuration in Django settings
   - Verify SMTP credentials
   - Check email server logs

4. **Document Upload Issues**:
   - Ensure media files are properly configured
   - Check file permissions on upload directory
   - Verify file size limits

### Support

For technical support or questions, please contact the development team.

## License

This project is proprietary software for MediSync.
