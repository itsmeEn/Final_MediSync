#!/bin/bash

echo "=================================================="
echo "MediSync 2FA Setup Script"
echo "=================================================="
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Virtual environment not detected"
    echo "Attempting to activate virtual environment..."
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo "✅ Virtual environment activated"
    else
        echo "❌ Virtual environment not found. Please activate it manually."
        exit 1
    fi
else
    echo "✅ Virtual environment is active: $VIRTUAL_ENV"
fi

echo ""
echo "Step 1: Installing 2FA dependencies..."
echo "----------------------------------------"
pip install pyotp==2.9.0 qrcode==7.4.2

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo ""
echo "Step 2: Running migrations..."
echo "----------------------------------------"
python manage.py migrate

if [ $? -eq 0 ]; then
    echo "✅ Migrations applied successfully"
else
    echo "❌ Failed to apply migrations"
    exit 1
fi

echo ""
echo "Step 3: Checking installation..."
echo "----------------------------------------"
python -c "import pyotp, qrcode; print('✅ All 2FA packages imported successfully')"

if [ $? -eq 0 ]; then
    echo "✅ 2FA installation verified"
else
    echo "❌ Failed to import 2FA packages"
    exit 1
fi

echo ""
echo "=================================================="
echo "✅ 2FA Setup Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Start the Django server: python manage.py runserver"
echo "2. Run the test script: python test_2fa_implementation.py"
echo "3. Read the documentation: 2FA_IMPLEMENTATION_GUIDE.md"
echo ""
echo "API Endpoints:"
echo "  - POST /users/2fa/enable/"
echo "  - POST /users/2fa/verify/"
echo "  - POST /users/2fa/disable/"
echo "  - POST /users/2fa/login/verify/"
echo ""
echo "=================================================="
