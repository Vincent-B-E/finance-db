accounts = []

def create_account(name, initial_balance):
    if initial_balance < 0:
        raise ValueError("Initial balance cannot be negative.")
    if name in [account["name"] for account in accounts]:
        raise ValueError("Account with this name already exists.")
    
    account = {
        "name": name,
        "balance": initial_balance,
        "transactions": []
    }
    accounts.append(account)
    return account

def deposit(name, amount):
    if amount <= 0:
        raise ValueError("Deposit amount must be greater than zero.")
    
    for account in accounts:
        if account["name"] == name:
            account["balance"] += amount
            account["transactions"].append({"type": "deposit", "amount": amount})
            return f"Deposit successful. New balance: ${account['balance']:.2f}"
        
    raise ValueError("Account not found.")

def withdraw(name, amount):
    if amount <= 0:
        raise ValueError("Withdrawal amount must be greater than zero.")
    
    for account in accounts:
        if account["name"] == name:
            if account["balance"] < amount:
                raise ValueError("Insufficient funds.")
            account["balance"] -= amount
            account["transactions"].append({"type": "withdrawal", "amount": amount})
            return f"Withdrawal successful. New balance: ${account['balance']:.2f}"

    raise ValueError("Account not found.")

def show_account(name):
    for i, account in enumerate(accounts, start=1):
        if account["name"] == name:
            print(f"Account {i}: Name: {account['name']}, Balance: ${account['balance']:.2f}")
            print("Transactions:")
            if any(account["transactions"]):
                for transaction in account["transactions"]:
                    print(f" - {transaction['type'].capitalize()}: ${transaction['amount']:.2f}")
            return

    raise ValueError("Account not found.")

def test_mini_bank():
    accounts_to_create = [
        ("Alice", 1000),
        ("Bob", 500),
        ("Charlie", 2000),
        ("Alice", 300)  # Duplicate; will be skipped
    ]

    for name, initial_balance in accounts_to_create:
        try:
            create_account(name, initial_balance)
        except ValueError as e:
            print(f"Could not create account for '{name}': {e}")

    # Test deposits
    transactions_to_test = [
        ("Alice", "deposit", 500),
        ("Bob", "deposit", 100),
        ("Charlie", "withdraw", -50),  # Invalid; will be skipped
        ("Alice", "deposit", 0),      # Invalid; will be skipped
        ("Bob", "withdraw", 200)
    ]

    for name, transaction_type, amount in transactions_to_test:
        try:
            if transaction_type == "deposit":
                deposit(name, amount)
            elif transaction_type == "withdraw":
                withdraw(name, amount)
        except ValueError as e:
            print(f"Could not {transaction_type} for '{name}': {e}")

    # Show account details
    show_account("Alice")
    show_account("Bob")
    show_account("Charlie")

if __name__ == "__main__":
    test_mini_bank()