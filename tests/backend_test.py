import requests
import sys
from datetime import datetime, timedelta

class MoneyBalancerAPITester:
    def __init__(self, base_url="https://moneyminder-32.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_expense_ids = []
        self.created_debt_ids = []

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text}")

            return success, response.json() if response.text and success else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_create_expense(self, title, amount, date, category):
        """Test creating an expense"""
        success, response = self.run_test(
            f"Create Expense - {title}",
            "POST",
            "expenses",
            200,
            data={
                "title": title,
                "amount": amount,
                "date": date,
                "category": category
            }
        )
        if success and 'id' in response:
            self.created_expense_ids.append(response['id'])
            return response['id']
        return None

    def test_get_expenses(self, filter_type=None):
        """Test getting expenses with optional filter"""
        params = {"filter": filter_type} if filter_type else None
        filter_text = f" (filter={filter_type})" if filter_type else ""
        success, response = self.run_test(
            f"Get Expenses{filter_text}",
            "GET",
            "expenses",
            200,
            params=params
        )
        return success, response if isinstance(response, list) else []

    def test_delete_expense(self, expense_id):
        """Test deleting an expense"""
        success, _ = self.run_test(
            f"Delete Expense {expense_id[:8]}",
            "DELETE",
            f"expenses/{expense_id}",
            200
        )
        return success

    def test_create_debt(self, name, amount, reason, date, debt_type):
        """Test creating a debt entry"""
        success, response = self.run_test(
            f"Create Debt - {name} ({debt_type})",
            "POST",
            "debts",
            200,
            data={
                "name": name,
                "amount": amount,
                "reason": reason,
                "date": date,
                "status": "pending",
                "debt_type": debt_type
            }
        )
        if success and 'id' in response:
            self.created_debt_ids.append(response['id'])
            return response['id']
        return None

    def test_get_debts(self):
        """Test getting all debts"""
        success, response = self.run_test(
            "Get Debts",
            "GET",
            "debts",
            200
        )
        return success, response if isinstance(response, list) else []

    def test_update_debt_status(self, debt_id, status):
        """Test updating debt status"""
        success, response = self.run_test(
            f"Update Debt Status to {status}",
            "PATCH",
            f"debts/{debt_id}",
            200,
            data={"status": status}
        )
        return success, response

    def test_delete_debt(self, debt_id):
        """Test deleting a debt"""
        success, _ = self.run_test(
            f"Delete Debt {debt_id[:8]}",
            "DELETE",
            f"debts/{debt_id}",
            200
        )
        return success

    def test_create_or_update_limit(self, weekly_limit, monthly_limit):
        """Test creating or updating spending limits"""
        success, response = self.run_test(
            "Create/Update Spending Limits",
            "POST",
            "limit",
            200,
            data={
                "weekly_limit": weekly_limit,
                "monthly_limit": monthly_limit
            }
        )
        return success, response

    def test_get_limit(self):
        """Test getting spending limits"""
        success, response = self.run_test(
            "Get Spending Limits",
            "GET",
            "limit",
            200
        )
        return success, response

    def test_get_summary(self):
        """Test getting summary with calculations"""
        success, response = self.run_test(
            "Get Summary",
            "GET",
            "summary",
            200
        )
        return success, response

def main():
    print("=" * 60)
    print("Money Balancer API Testing")
    print("=" * 60)
    
    tester = MoneyBalancerAPITester()
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    # Test 1: Create Expenses
    print("\n" + "=" * 60)
    print("TEST SUITE 1: EXPENSES")
    print("=" * 60)
    
    expense1_id = tester.test_create_expense("Grocery Shopping", 50.00, today, "Food")
    expense2_id = tester.test_create_expense("Uber Ride", 15.50, today, "Travel")
    expense3_id = tester.test_create_expense("Netflix Subscription", 12.99, week_ago, "Entertainment")
    
    # Test 2: Get Expenses
    success, all_expenses = tester.test_get_expenses()
    if success:
        print(f"   Total expenses retrieved: {len(all_expenses)}")
    
    success, day_expenses = tester.test_get_expenses("day")
    if success:
        print(f"   Today's expenses: {len(day_expenses)}")
    
    success, week_expenses = tester.test_get_expenses("week")
    if success:
        print(f"   This week's expenses: {len(week_expenses)}")
    
    success, month_expenses = tester.test_get_expenses("month")
    if success:
        print(f"   This month's expenses: {len(month_expenses)}")
    
    # Test 3: Debts
    print("\n" + "=" * 60)
    print("TEST SUITE 2: DEBTS")
    print("=" * 60)
    
    debt1_id = tester.test_create_debt("John Doe", 100.00, "Lunch money", today, "gave")
    debt2_id = tester.test_create_debt("Jane Smith", 50.00, "Movie tickets", today, "owe")
    
    success, all_debts = tester.test_get_debts()
    if success:
        print(f"   Total debts retrieved: {len(all_debts)}")
    
    # Test 4: Update Debt Status
    if debt1_id:
        success, updated_debt = tester.test_update_debt_status(debt1_id, "paid")
        if success and updated_debt.get('status') == 'paid':
            print("   ✅ Debt status updated correctly")
        else:
            print("   ❌ Debt status not updated correctly")
    
    # Test 5: Spending Limits
    print("\n" + "=" * 60)
    print("TEST SUITE 3: SPENDING LIMITS")
    print("=" * 60)
    
    success, limit_response = tester.test_create_or_update_limit(500.00, 2000.00)
    if success:
        print(f"   Weekly limit: ${limit_response.get('weekly_limit', 0)}")
        print(f"   Monthly limit: ${limit_response.get('monthly_limit', 0)}")
    
    success, get_limit_response = tester.test_get_limit()
    if success:
        print(f"   Retrieved weekly limit: ${get_limit_response.get('weekly_limit', 0)}")
        print(f"   Retrieved monthly limit: ${get_limit_response.get('monthly_limit', 0)}")
    
    # Test 6: Summary and Warning System
    print("\n" + "=" * 60)
    print("TEST SUITE 4: SUMMARY & WARNING SYSTEM")
    print("=" * 60)
    
    success, summary = tester.test_get_summary()
    if success:
        print(f"   Today's total: ${summary.get('total_today', 0)}")
        print(f"   Week's total: ${summary.get('total_week', 0)}")
        print(f"   Month's total: ${summary.get('total_month', 0)}")
        print(f"   Weekly limit: ${summary.get('weekly_limit', 0)}")
        print(f"   Monthly limit: ${summary.get('monthly_limit', 0)}")
        print(f"   Remaining week: ${summary.get('remaining_week', 0)}")
        print(f"   Remaining month: ${summary.get('remaining_month', 0)}")
        print(f"   Money gave: ${summary.get('money_gave', 0)}")
        print(f"   Money owe: ${summary.get('money_owe', 0)}")
        print(f"   Weekly warning: {summary.get('weekly_warning', 'none')}")
        print(f"   Monthly warning: {summary.get('monthly_warning', 'none')}")
        
        # Verify warning calculations
        weekly_limit = summary.get('weekly_limit', 0)
        total_week = summary.get('total_week', 0)
        if weekly_limit > 0:
            percent = (total_week / weekly_limit) * 100
            expected_warning = "red" if percent >= 100 else ("yellow" if percent >= 80 else "none")
            actual_warning = summary.get('weekly_warning', 'none')
            if expected_warning == actual_warning:
                print(f"   ✅ Weekly warning calculation correct ({percent:.1f}%)")
            else:
                print(f"   ❌ Weekly warning incorrect - Expected: {expected_warning}, Got: {actual_warning}")
    
    # Test 7: Test Warning System with High Spending
    print("\n" + "=" * 60)
    print("TEST SUITE 5: WARNING SYSTEM (80% & 100%)")
    print("=" * 60)
    
    # Set low limit to trigger warnings
    tester.test_create_or_update_limit(100.00, 500.00)
    
    # Add expenses to reach 80% (yellow warning)
    tester.test_create_expense("Test Expense 1", 40.00, today, "Other")
    tester.test_create_expense("Test Expense 2", 40.00, today, "Other")
    
    success, summary_80 = tester.test_get_summary()
    if success:
        weekly_warning = summary_80.get('weekly_warning', 'none')
        total_week = summary_80.get('total_week', 0)
        print(f"   Total week spending: ${total_week}")
        print(f"   Weekly warning at 80%: {weekly_warning}")
        if weekly_warning == 'yellow':
            print("   ✅ Yellow warning triggered correctly at 80%")
        else:
            print(f"   ❌ Expected 'yellow' warning, got '{weekly_warning}'")
    
    # Add more to reach 100% (red warning)
    tester.test_create_expense("Test Expense 3", 30.00, today, "Other")
    
    success, summary_100 = tester.test_get_summary()
    if success:
        weekly_warning = summary_100.get('weekly_warning', 'none')
        total_week = summary_100.get('total_week', 0)
        print(f"   Total week spending: ${total_week}")
        print(f"   Weekly warning at 100%: {weekly_warning}")
        if weekly_warning == 'red':
            print("   ✅ Red warning triggered correctly at 100%")
        else:
            print(f"   ❌ Expected 'red' warning, got '{weekly_warning}'")
    
    # Test 8: Delete Operations
    print("\n" + "=" * 60)
    print("TEST SUITE 6: DELETE OPERATIONS")
    print("=" * 60)
    
    if expense1_id:
        tester.test_delete_expense(expense1_id)
    
    if debt2_id:
        tester.test_delete_debt(debt2_id)
    
    # Print final results
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    success_rate = (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0
    print(f"📈 Success rate: {success_rate:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ {tester.tests_run - tester.tests_passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
