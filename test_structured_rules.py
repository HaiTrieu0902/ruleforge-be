from app.services.rule_generator import RuleGenerator
import asyncio
import json

async def test_structured_rules():
    rule_generator = RuleGenerator()
    
    # Vietnamese loan application contract
    vietnamese_contract = '''
    Hợp đồng vay vốn ngân hàng ABC
    
    Điều 1: Điều kiện vay vốn
    - Người vay phải có tuổi từ 18 đến 65 tuổi
    - Thời gian làm việc tối thiểu 12 tháng
    - Lương tối thiểu 10.000.000 VNĐ/tháng
    - Phải có bảo hiểm xã hội ít nhất 6 tháng
    
    Điều 2: Tính toán thu nhập
    - Nếu người vay là công chức thì thu nhập tham chiếu = lương cơ bản x 1.5
    - Nếu người vay là nhân viên tư nhân có bảo hiểm đầy đủ thì thu nhập = lương x 0.8
    - Nếu không có bảo hiểm thì từ chối vay
    
    Điều 3: Phương thức thanh toán
    - Chuyển khoản: phí 0%
    - Tiền mặt: phí 2%
    - Nếu tuổi > 60 và không có người bảo lãnh thì từ chối
    
    Điều 4: Xử lý vi phạm
    - Trễ hạn dưới 30 ngày: phạt 5% số tiền gốc
    - Trễ hạn trên 30 ngày: phạt 10% và đình chỉ hợp đồng
    '''
    
    # English loan contract
    english_contract = '''
    Bank ABC Loan Agreement
    
    Article 1: Loan Eligibility
    - Applicant must be between 18 and 65 years old
    - Minimum work experience of 12 months
    - Minimum salary of $2,000/month
    - Must have social insurance for at least 6 months
    
    Article 2: Income Calculation
    - If applicant is civil servant then reference income = base salary x 1.5
    - If applicant is private employee with full insurance then income = salary x 0.8
    - If no insurance then reject loan
    
    Article 3: Payment Method
    - Bank transfer: 0% fee
    - Cash payment: 2% fee
    - If age > 60 and no guarantor then reject
    
    Article 4: Violation Handling
    - Late payment under 30 days: penalty 5% of principal
    - Late payment over 30 days: penalty 10% and terminate contract
    '''
    
    print("🇻🇳 Testing Vietnamese contract structured rules...")
    try:
        vietnamese_rules = await rule_generator.generate_rules(vietnamese_contract, "loan_contract")
        print("=== VIETNAMESE STRUCTURED RULES ===")
        print(f"📊 Generated {len(vietnamese_rules.get('business_rules', []))} business rules")
        print(f"📋 Identified {len(vietnamese_rules.get('variables', []))} variables")
        print(f"⚙️ Found {len(vietnamese_rules.get('constants', []))} constants")
        
        # Show first rule as example
        if vietnamese_rules.get('business_rules'):
            first_rule = vietnamese_rules['business_rules'][0]
            print(f"\n📝 Example Rule: {first_rule.get('rule_name')}")
            print(f"🔧 Category: {first_rule.get('category')}")
            print(f"📐 Logic:\n{first_rule.get('rule_logic', 'No logic generated')}")
            print(f"🔗 Variables: {first_rule.get('variables_used', [])}")
        
        print("\n" + "="*50)
        
    except Exception as e:
        print(f"❌ Error testing Vietnamese: {str(e)}")
    
    print("🇺🇸 Testing English contract structured rules...")
    try:
        english_rules = await rule_generator.generate_rules(english_contract, "loan_contract")
        print("=== ENGLISH STRUCTURED RULES ===")
        print(f"📊 Generated {len(english_rules.get('business_rules', []))} business rules")
        print(f"📋 Identified {len(english_rules.get('variables', []))} variables")
        print(f"⚙️ Found {len(english_rules.get('constants', []))} constants")
        
        # Show first rule as example
        if english_rules.get('business_rules'):
            first_rule = english_rules['business_rules'][0]
            print(f"\n📝 Example Rule: {first_rule.get('rule_name')}")
            print(f"🔧 Category: {first_rule.get('category')}")
            print(f"📐 Logic:\n{first_rule.get('rule_logic', 'No logic generated')}")
            print(f"🔗 Variables: {first_rule.get('variables_used', [])}")
        
        # Show example variables if available
        if english_rules.get('variables'):
            print(f"\n📋 Example Variables:")
            for var in english_rules['variables'][:3]:  # Show first 3 variables
                print(f"  • {var.get('variable_name')}: {var.get('description')} ({var.get('data_type')})")
        
        # Save to file for inspection
        with open('d:/learning/ruleforge-be/test_structured_rules_output.json', 'w', encoding='utf-8') as f:
            json.dump(english_rules, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Full results saved to test_structured_rules_output.json")
        
    except Exception as e:
        print(f"❌ Error testing English: {str(e)}")
    
    finally:
        rule_generator.close()

if __name__ == "__main__":
    asyncio.run(test_structured_rules())