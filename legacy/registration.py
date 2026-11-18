registered_users = []
failed_registrations = []

def validate_name (name):
    if len(name) < 3:
        return False
    elif not name.isalpha():
        return False
    return True

def validate_email(email):
    if "@" not in email or "." not in email:
        return False
    return True

def validate_password(password):
    if len(password) < 8:
        return False
    elif not any(char.isupper() for char in password):
        return False
    elif not any(char.isdigit() for char in password):
        return False
    return True

def validate_user_data(name, email, password):
    if not validate_name(name):
        raise ValueError("Invalid name. Name must be at least 3 characters long and contain only letters.")
    if not validate_email(email):
        raise ValueError("Invalid email. Email must contain '@' and '.'")
    if not validate_password(password):
        raise ValueError("Invalid password. Password must be at least 8 characters long, contain at least one uppercase letter and one digit.")
    return True, "User data is valid."

def create_user_account(name, email, password):
    if any(user['email'] == email for user in registered_users):
        return False, "Email already registered."
    else:
        try:
            validate_user_data(name, email, password)
            registered_users.append({
                "name": name,
                "email": email,
                "password": password
        })
            return True, "User account created successfully."
        except ValueError as e:
            failed_registrations.append({
                "email": email,
                "error": str(e)
            })
            return False, str(e)

def unit_test_registration():
    # Test cases for registration:
    test_cases = [
        {"name": "John", "email": "john@example.com", "password": "Password123"},
        {"name": "John", "email": "john@example.com", "password": "Password456"},
        {"name": "Jo", "email": "jo@example.com", "password": "Password789"},
        {"name": "Alice", "email": "aliceexample.com", "password": "Password123"},
        {"name": "Bob", "email": "bob@example.com", "password": "password"}
    ]
    for case in test_cases:
        success, message = create_user_account(case["name"], case["email"], case["password"])
        print(f"Test case: {case}, Status: {success}, Message: {message}")
    print(f"Registered users: {registered_users}")
    print(f"Failed registrations: {failed_registrations}")


if __name__ == "__main__":
    unit_test_registration()
