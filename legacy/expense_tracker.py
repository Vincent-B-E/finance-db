expenses = []

def add_expense(amount, category, description):
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    else:
        expense = {
            "amount": amount,
            "category": category,
            "description": description
        }
        expenses.append(expense)
    return expenses[-1]

def calculate_total_expenses():
    total = sum(expense["amount"] for expense in expenses)
    return total

def calculate_total_by_category(category):
    total = sum(expense["amount"] for expense in expenses if expense["category"] == category)
    return total

def show_expenses(): 
    for i, expense in enumerate(expenses, start=1):
        print(f"{i}. Amount: {expense['amount']}, Category: {expense['category']}, Description: {expense['description']}")

def test_expense_tracker():
    expenses_to_add = [
        (50, "Food", "Lunch"),
        (-20, "Transport", "Bus fare"),  # Invalid; will be skipped
        (100, "Food", "Dinner"),
        (30, "Entertainment", "Movie ticket"),
        (0, "Misc", "Stationery"),  # Invalid; will be skipped
        (25, "Transport", "Taxi fare")
    ]

    for amount, category, description in expenses_to_add:
        try:
            add_expense(amount, category, description)
        except ValueError as e:
            print(f"Could not add expense '{description}': {e}")

    show_expenses()
    
    print("All Expenses:")
    show_expenses()
    
    total = calculate_total_expenses()
    print(f"Total Expenses: {total}")
    
    for cat in set(expense["category"] for expense in expenses):
        total_by_category = calculate_total_by_category(cat)
        print(f"Total {cat} Expenses: {total_by_category}")

if __name__ == "__main__":
    test_expense_tracker()


