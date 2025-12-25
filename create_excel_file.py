import openpyxl

def create_valid_excel_file():
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"

    # Ajouter des données
    data = [
        ["Attendance", "Name", "Department"],
        [8, "John Doe", "HR"],
        [7, "Jane Smith", "Finance"],
        [9, "Emily Johnson", "IT"],
        [6, "Michael Brown", "Marketing"],
        [10, "Chris Davis", "Sales"],
    ]

    for row in data:
        sheet.append(row)

    # Sauvegarder le fichier
    workbook.save("uploads/example.xlsx")

if __name__ == "__main__":
    create_valid_excel_file()