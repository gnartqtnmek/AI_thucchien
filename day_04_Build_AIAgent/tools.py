from langchain_core.tools import tool

# =====================================================================
# MOCK DATA - Dữ liệu giả lập hệ thống du lịch
# Lưu ý: Giá cả có logic (VD: cuối tuần, ngày lễ đắt hơn, hạng cao hơn đắt hơn, nhiều dịch vụ hơn đắt hơn...)
# Sinh viên cần đọc hiểu data để debug test cases
# ======================================================================

from langchain_core.tools import tool

# =====================================================================
# MOCK DATA - Dữ liệu giả lập hệ thống du lịch
# =====================================================================

FLIGHTS_DB = {
    ("Hà Nội", "Đà Nẵng"): [
        {"airline": "Vietnam Airlines", "departure": "06:00", "arrival": "07:20", "price": 1_450_000, "class": "economy"},
        {"airline": "Vietnam Airlines", "departure": "14:00", "arrival": "15:20", "price": 2_800_000, "class": "business"},
        {"airline": "VietJet Air", "departure": "08:30", "arrival": "09:50", "price": 890_000, "class": "economy"},
        {"airline": "Bamboo Airways", "departure": "11:00", "arrival": "12:20", "price": 1_200_000, "class": "economy"},
    ],
    ("Hà Nội", "Phú Quốc"): [
        {"airline": "Vietnam Airlines", "departure": "07:00", "arrival": "09:15", "price": 2_100_000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "10:00", "arrival": "12:15", "price": 1_350_000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "16:00", "arrival": "18:15", "price": 1_100_000, "class": "economy"},
    ],
    ("Hà Nội", "Hồ Chí Minh"): [
        {"airline": "Vietnam Airlines", "departure": "06:00", "arrival": "08:10", "price": 1_600_000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "07:30", "arrival": "09:40", "price": 950_000, "class": "economy"},
        {"airline": "Bamboo Airways", "departure": "12:00", "arrival": "14:10", "price": 1_300_000, "class": "economy"},
        {"airline": "Vietnam Airlines", "departure": "18:00", "arrival": "20:10", "price": 3_200_000, "class": "business"},
    ],
    ("Hồ Chí Minh", "Đà Nẵng"): [
        {"airline": "Vietnam Airlines", "departure": "09:00", "arrival": "10:20", "price": 1_300_000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "13:00", "arrival": "14:20", "price": 780_000, "class": "economy"},
    ],
    ("Hồ Chí Minh", "Phú Quốc"): [
        {"airline": "Vietnam Airlines", "departure": "08:00", "arrival": "09:00", "price": 1_100_000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "15:00", "arrival": "16:00", "price": 650_000, "class": "economy"},
    ],
}

HOTELS_DB = {
    "Đà Nẵng": [
        {"name": "Mường Thanh Luxury", "stars": 5, "price_per_night": 1_800_000, "area": "Mỹ Khê", "rating": 4.5},
        {"name": "Sala Danang Beach", "stars": 4, "price_per_night": 1_200_000, "area": "Mỹ Khê", "rating": 4.3},
        {"name": "Fivitel Danang", "stars": 3, "price_per_night": 650_000, "area": "Sơn Trà", "rating": 4.1},
        {"name": "Memory Hostel", "stars": 2, "price_per_night": 250_000, "area": "Hải Châu", "rating": 4.6},
        {"name": "Christina's Homestay", "stars": 2, "price_per_night": 350_000, "area": "An Thượng", "rating": 4.7},
    ],
    "Phú Quốc": [
        {"name": "Vinpearl Resort", "stars": 5, "price_per_night": 3_500_000, "area": "Bãi Dài", "rating": 4.4},
        {"name": "Sol by Meliá", "stars": 4, "price_per_night": 1_500_000, "area": "Bãi Trường", "rating": 4.2},
        {"name": "Lahana Resort", "stars": 3, "price_per_night": 800_000, "area": "Dương Đông", "rating": 4.0},
        {"name": "9Station Hostel", "stars": 2, "price_per_night": 200_000, "area": "Dương Đông", "rating": 4.5},
    ],
    "Hồ Chí Minh": [
        {"name": "Rex Hotel", "stars": 5, "price_per_night": 2_800_000, "area": "Quận 1", "rating": 4.3},
        {"name": "Liberty Central", "stars": 4, "price_per_night": 1_400_000, "area": "Quận 1", "rating": 4.1},
        {"name": "Cochin Zen Hotel", "stars": 3, "price_per_night": 550_000, "area": "Quận 3", "rating": 4.4},
        {"name": "The Common Room", "stars": 2, "price_per_night": 180_000, "area": "Quận 1", "rating": 4.6},
    ],
}


# =====================================================================
# HÀM PHỤ TRỢ (Helper Functions)
# =====================================================================
def format_vnd(amount: int) -> str:
    """Định dạng số tiền int thành chuỗi tiền tệ VNĐ (VD: 1.500.000đ)"""
    return f"{amount:,.0f}".replace(",", ".") + "đ"


# =====================================================================
# KHỞI TẠO TOOLS CHO AGENT
# =====================================================================

@tool
def search_flights(origin: str, destination: str) -> str:
    """
    Tìm kiếm các chuyến bay giữa hai thành phố.
    Tham số:
    - origin: thành phố khởi hành (VD: 'Hà Nội', 'Hồ Chí Minh')
    - destination: thành phố đến (VD: 'Đà Nẵng', 'Phú Quốc')
    Trả về danh sách chuyến bay với hãng, giờ bay, giá vé.
    Nếu không tìm thấy tuyến bay, trả về thông báo không có chuyến.
    """
    # 1. Tra cứu FLIGHTS_DB với key (origin, destination)
    flights = FLIGHTS_DB.get((origin, destination))
    
    # 2. Xử lý logic nếu không tìm thấy chiều đi, thử tra chiều ngược lại
    if not flights:
        flights = FLIGHTS_DB.get((destination, origin))
        if not flights:
            return f"Không tìm thấy chuyến bay từ {origin} đến {destination} (hoặc ngược lại)."
        else:
            result_str = f"Chỉ tìm thấy chuyến bay theo chiều ngược lại ({destination} -> {origin}):\n"
    else:
        result_str = f"Danh sách chuyến bay từ {origin} đến {destination}:\n"
    
    # 3. Format danh sách trả về cho Agent dễ đọc
    for f in flights:
        price_str = format_vnd(f['price'])
        result_str += f"- Hãng: {f['airline']}, Giờ: {f['departure']} -> {f['arrival']}, Hạng: {f['class']}, Giá: {price_str}\n"
        
    return result_str


@tool
def search_hotels(city: str, max_price_per_night: int = 99999999) -> str:
    """
    Tìm kiếm khách sạn tại một thành phố, có thể lọc theo giá tối đa mỗi đêm.
    Tham số:
    - city: tên thành phố (VD: 'Đà Nẵng', 'Phú Quốc', 'Hồ Chí Minh')
    - max_price_per_night: giá tối đa mỗi đêm (VNĐ), mặc định không giới hạn
    Trả về danh sách khách sạn phù hợp với tên, số sao, giá, khu vực, rating.
    """
    # 1. Tra cứu HOTELS_DB
    hotels = HOTELS_DB.get(city)
    if not hotels:
        return f"Hiện tại chưa có dữ liệu khách sạn tại thành phố {city}."
        
    # 2. Lọc theo max_price_per_night
    filtered_hotels = [h for h in hotels if h['price_per_night'] <= max_price_per_night]
    
    # 3. Sắp xếp theo rating giảm dần
    filtered_hotels.sort(key=lambda x: x['rating'], reverse=True)
    
    # Xử lý nếu lọc xong không còn khách sạn nào
    if not filtered_hotels:
        return f"Không tìm thấy khách sạn tại {city} với giá dưới {format_vnd(max_price_per_night)}/đêm. Hãy thử tăng ngân sách."
        
    # 4. Format kết quả
    result_str = f"Danh sách khách sạn tại {city} (Lọc giá <= {format_vnd(max_price_per_night)}/đêm):\n"
    for h in filtered_hotels:
        price_str = format_vnd(h['price_per_night'])
        result_str += f"- {h['name']} ({h['stars']} sao) | Khu vực: {h['area']} | Rating: {h['rating']} | Giá: {price_str}/đêm\n"
        
    return result_str


@tool
def calculate_budget(total_budget: int, expenses: str) -> str:
    """
    Tính toán ngân sách còn lại sau khi trừ các khoản chi phí.
    Tham số:
    - total_budget: tổng ngân sách ban đầu (VNĐ)
    - expenses: chuỗi mô tả các khoản chi, mỗi khoản cách nhau bởi dấu phẩy, 
                định dạng 'tên_khoản:số_tiền' (VD: 'vé_máy_bay:890000,khách_sạn:650000')
    Trả về bảng chi tiết các khoản chi và số tiền còn lại.
    Nếu vượt ngân sách, cảnh báo rõ ràng số tiền thiếu.
    """
    try:
        # 1. Parse chuỗi expenses
        expense_items = expenses.split(",")
        parsed_expenses = {}
        total_expense = 0
        
        for item in expense_items:
            name, amount_str = item.split(":")
            name = name.strip().replace('_', ' ').capitalize() # Làm đẹp tên khoản chi
            amount = int(amount_str.strip())
            parsed_expenses[name] = amount
            total_expense += amount
            
        # 2. Tính số tiền còn lại
        balance = total_budget - total_expense
        
        # 3. Format bảng chi tiết
        result = "Bảng chi phí:\n"
        for name, amount in parsed_expenses.items():
            result += f"  - {name}: {format_vnd(amount)}\n"
            
        result += "---\n"
        result += f"Tổng chi: {format_vnd(total_expense)}\n"
        result += f"Ngân sách ban đầu: {format_vnd(total_budget)}\n"
        
        # 4. Kiểm tra âm ngân sách
        if balance < 0:
            result += f"Còn lại: {format_vnd(balance)}\n"
            result += f"-> CẢNH BÁO: Vượt ngân sách {format_vnd(abs(balance))}! Cần điều chỉnh lại."
        else:
            result += f"Còn lại: {format_vnd(balance)}"
            
        return result
        
    except Exception:
        # Xử lý lỗi nếu chuỗi expenses Agent truyền vào sai format
        return (
            "Lỗi format khi gọi tool calculate_budget. "
            "Vui lòng truyền expenses theo đúng định dạng: 'khoản_1:tiền_1,khoản_2:tiền_2'. "
            "Ví dụ: 'vé_máy_bay:1500000,khách_sạn:800000'."
        )