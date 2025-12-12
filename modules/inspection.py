import os

def inspect_file(file_path, signature="INJECTED"):
    """
    Mengecek apakah file hasil injeksi benar-benar mengandung bug.
    Mengembalikan True jika Valid, False jika Gagal.
    """
    if not os.path.exists(file_path):
        return False, "File Not Found"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if signature in content:
                return True, "Success"
            else:
                return False, "Signature Missing"
    except Exception as e:
        return False, str(e)