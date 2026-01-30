
import sys
import os

# Add current directory to path so 'app' is found
sys.path.append(os.getcwd())

print("Attempting to import AdminService...")
try:
    from app.services.admin import AdminService
    print("✅ Import SUCCESSFUL!")
    print(f"Handle Method: {AdminService.handle_command}")
except Exception as e:
    print("❌ Import FAILED")
    import traceback
    traceback.print_exc()
