import gspread
from gspread.utils import rowcol_to_a1
from google.oauth2.service_account import Credentials
from urllib.parse import quote


def connect_to_sheet(spreadsheet_name: str):
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    client = gspread.authorize(creds)
    return client.open(spreadsheet_name).sheet1


def add_act_to_registry(data: dict):

    sheet = connect_to_sheet("Реестр Актов")
    descriptions = data["description"]
    start_row = len(sheet.get_all_values()) + 1

    empty_placeholder = " "
    
    filename = data['file_path'].replace("acts/", "")
    file_path_encoded = quote(filename)
    file_url = f"http://backend:8000/download/{file_path_encoded}"
    print('file_url', file_url)
    
    # Подготовка строк описаний
    lines = []
    for key in sorted(descriptions, key=int):
        block = descriptions[key]
        texts = block.get("texts", [])
        photos = block.get("photos", [])

        if texts:
            for t in texts:
                lines.append(["", "", "", t, empty_placeholder, empty_placeholder])  # Пустые E и F
        elif photos:
            # Добавляем одну строку с "Только фото"
            lines.append(["", "", "", "Только фото", empty_placeholder, empty_placeholder])
        else:
            lines.append(["", "", "", "Пусто", empty_placeholder, empty_placeholder])

    total_lines = len(lines)
    end_row = start_row + total_lines - 1

    # Сначала вставляем строки (чтобы они не сдвинули то, что мы потом обновим)
    sheet.insert_rows(lines, row=start_row)

    # Затем вставляем данные в объединяемые ячейки
    sheet.update_cell(start_row, 1, data["act_id"])
    sheet.update_cell(start_row, 2, data["act_name"])
    sheet.update_cell(start_row, 3, f'=HYPERLINK("{file_url}"; "{data["act_name"]}")')
    
    # Объединение ячеек в столбцах: A (1), B (2), C (3), E (5), F (6)
    merge_ranges = []
    for col in [1, 2, 3]:
        merge_ranges.append({
            "mergeType": "MERGE_ALL",
            "range": {
                "sheetId": sheet._properties['sheetId'],
                "startRowIndex": start_row - 1,
                "endRowIndex": end_row,
                "startColumnIndex": col - 1,
                "endColumnIndex": col,
            }
        })

    sheet.spreadsheet.batch_update({
        "requests": [{"mergeCells": r} for r in merge_ranges]
    })
