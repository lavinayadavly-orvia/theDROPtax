import requests
import sys
import json
from datetime import datetime

class DropTaxAPITester:
    def __init__(self):
        self.base_url = "http://localhost:8000/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.drug_ids = []

    def log_test(self, name, success, details="", expected_status=200, actual_status=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        
        result = {
            "test": name,
            "status": status,
            "success": success,
            "details": details,
            "expected_status": expected_status,
            "actual_status": actual_status
        }
        self.test_results.append(result)
        
        print(f"\n{status} - {name}")
        if not success:
            print(f"  Expected: {expected_status}, Got: {actual_status}")
        if details:
            print(f"  Details: {details}")

    def test_api_root(self):
        """Test API root endpoint"""
        try:
            response = requests.get(f"{self.base_url}/")
            success = response.status_code == 200
            
            if success:
                data = response.json()
                details = f"Message: {data.get('message', 'N/A')}, Version: {data.get('version', 'N/A')}"
            else:
                details = f"Failed to get root endpoint: {response.text}"
                
            self.log_test("API Root Endpoint", success, details, 200, response.status_code)
            return success
        except Exception as e:
            self.log_test("API Root Endpoint", False, f"Exception: {str(e)}")
            return False

    def test_regions_endpoint(self):
        """Test regions endpoint"""
        try:
            response = requests.get(f"{self.base_url}/regions")
            success = response.status_code == 200
            
            if success:
                regions = response.json()
                details = f"Found {len(regions)} regions: {', '.join([r['name'] for r in regions])}"
            else:
                details = f"Failed to get regions: {response.text}"
                
            self.log_test("Regions Endpoint", success, details, 200, response.status_code)
            return success, regions if success else []
        except Exception as e:
            self.log_test("Regions Endpoint", False, f"Exception: {str(e)}")
            return False, []

    def test_drug_search(self):
        """Test drug search functionality"""
        try:
            # Test empty search (should return all drugs)
            response = requests.get(f"{self.base_url}/drugs/search")
            success = response.status_code == 200
            
            if success:
                drugs = response.json()
                self.drug_ids = [drug['id'] for drug in drugs]
                details = f"Found {len(drugs)} drugs: {', '.join([d['name'] for d in drugs])}"
            else:
                details = f"Failed to search drugs: {response.text}"
                
            self.log_test("Drug Search (All)", success, details, 200, response.status_code)
            
            # Test search with query
            if success:
                response = requests.get(f"{self.base_url}/drugs/search?q=Pomali")
                search_success = response.status_code == 200
                if search_success:
                    search_drugs = response.json()
                    search_details = f"Search 'Pomali' found {len(search_drugs)} results"
                else:
                    search_details = f"Search query failed: {response.text}"
                    
                self.log_test("Drug Search (Query)", search_success, search_details, 200, response.status_code)
                return success and search_success, drugs if success else []
            
            return success, drugs if success else []
        except Exception as e:
            self.log_test("Drug Search", False, f"Exception: {str(e)}")
            return False, []

    def test_drug_detail(self, drug_id):
        """Test drug detail endpoint"""
        try:
            response = requests.get(f"{self.base_url}/drugs/{drug_id}")
            success = response.status_code == 200
            
            if success:
                drug = response.json()
                details = f"Drug: {drug.get('name')} - {drug.get('indication')}"
            else:
                details = f"Failed to get drug detail: {response.text}"
                
            self.log_test(f"Drug Detail ({drug_id[:8]})", success, details, 200, response.status_code)
            return success, drug if success else None
        except Exception as e:
            self.log_test(f"Drug Detail ({drug_id[:8]})", False, f"Exception: {str(e)}")
            return False, None

    def test_black_box_calculation(self, drug_id, region_code="IN"):
        """Test Black Box calculation endpoint"""
        try:
            response = requests.post(f"{self.base_url}/calculate?drug_id={drug_id}&region_code={region_code}")
            success = response.status_code == 200
            
            if success:
                calc = response.json()
                details = f"Total Liability: {calc.get('total_liability', 'N/A')}, Drug Cost: {calc.get('drug_cost', 'N/A')}"
            else:
                details = f"Failed Black Box calculation: {response.text}"
                
            self.log_test(f"Black Box Calc ({region_code})", success, details, 200, response.status_code)
            return success, calc if success else None
        except Exception as e:
            self.log_test(f"Black Box Calc ({region_code})", False, f"Exception: {str(e)}")
            return False, None

    def test_pap_recommendation(self, drug_id, region_code="IN"):
        """Test PAP recommendation endpoint"""
        try:
            response = requests.post(
                f"{self.base_url}/pap/recommend?drug_id={drug_id}&target_roi=3.0&patient_wallet_monthly=50000&region_code={region_code}"
            )
            success = response.status_code == 200
            
            if success:
                pap = response.json()
                details = f"PAP Scheme: {pap.get('recommended_scheme', 'N/A')[:50]}..."
            else:
                details = f"Failed PAP recommendation: {response.text}"
                
            self.log_test(f"PAP Recommendation ({region_code})", success, details, 200, response.status_code)
            return success, pap if success else None
        except Exception as e:
            self.log_test(f"PAP Recommendation ({region_code})", False, f"Exception: {str(e)}")
            return False, None

    def test_news_endpoint(self, drug_id):
        """Test news endpoint"""
        try:
            response = requests.get(f"{self.base_url}/news/{drug_id}")
            success = response.status_code == 200
            
            if success:
                news = response.json()
                details = f"Found {len(news)} news items"
            else:
                details = f"Failed to get news: {response.text}"
                
            self.log_test(f"News Feed ({drug_id[:8]})", success, details, 200, response.status_code)
            return success, news if success else []
        except Exception as e:
            self.log_test(f"News Feed ({drug_id[:8]})", False, f"Exception: {str(e)}")
            return False, []

    def test_pdf_generation(self, drug_id, region_code="IN"):
        """Test PDF generation endpoint"""
        try:
            response = requests.post(f"{self.base_url}/dossier/generate?drug_id={drug_id}&region_code={region_code}")
            success = response.status_code == 200
            
            if success:
                # Check if response is PDF (binary content)
                content_type = response.headers.get('content-type', '')
                is_pdf = 'application/pdf' in content_type
                details = f"PDF generated successfully, Content-Type: {content_type}, Size: {len(response.content)} bytes"
            else:
                details = f"Failed PDF generation: {response.text}"
                is_pdf = False
                
            final_success = success and is_pdf
            self.log_test(f"PDF Generation ({region_code})", final_success, details, 200, response.status_code)
            return final_success
        except Exception as e:
            self.log_test(f"PDF Generation ({region_code})", False, f"Exception: {str(e)}")
            return False

    def run_comprehensive_tests(self):
        """Run all API tests"""
        print("🧪 Starting DROP Tax Commercial Suite API Testing")
        print("=" * 60)
        
        # Test 1: API Root
        if not self.test_api_root():
            print("❌ Critical: API Root endpoint failed. Stopping tests.")
            return self.generate_report()
        
        # Test 2: Regions
        regions_success, regions = self.test_regions_endpoint()
        if not regions_success:
            print("❌ Critical: Regions endpoint failed. Stopping tests.")
            return self.generate_report()
        
        # Test 3: Drug Search
        drugs_success, drugs = self.test_drug_search()
        if not drugs_success or not self.drug_ids:
            print("❌ Critical: Drug search failed or no drugs found. Stopping tests.")
            return self.generate_report()
        
        # Test 4-8: Use first drug for detailed testing
        test_drug_id = self.drug_ids[0]
        
        # Test 4: Drug Detail
        drug_success, drug_data = self.test_drug_detail(test_drug_id)
        
        # Test 5-7: Black Box Calculation for different regions
        for region in regions:
            self.test_black_box_calculation(test_drug_id, region['code'])
        
        # Test 8-10: PAP Recommendations for different regions  
        for region in regions:
            self.test_pap_recommendation(test_drug_id, region['code'])
        
        # Test 11: News Feed
        self.test_news_endpoint(test_drug_id)
        
        # Test 12-14: PDF Generation for different regions
        for region in regions:
            self.test_pdf_generation(test_drug_id, region['code'])
        
        return self.generate_report()

    def generate_report(self):
        """Generate final test report"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed / self.tests_run * 100):.1f}%" if self.tests_run > 0 else "0%")
        
        failed_tests = [t for t in self.test_results if not t['success']]
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        
        # Return exit code: 0 for success, 1 for failures
        return 0 if self.tests_passed == self.tests_run else 1

def main():
    """Main test execution"""
    tester = DropTaxAPITester()
    return tester.run_comprehensive_tests()

if __name__ == "__main__":
    sys.exit(main())