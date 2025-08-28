import gspread
from gspread.utils import a1_to_rowcol, a1_range_to_grid_range
from gspread_formatting import CellFormat, Color, format_cell_range, get_effective_format
from google.oauth2.service_account import Credentials

PASTEL_COLORS = {
	"red":     (0.95, 0.6, 0.6),
    "green":   (0.6, 0.9, 0.6),
    "blue":    (0.6, 0.75, 0.95),
    "yellow":  (0.98, 0.95, 0.6),
    "magenta": (0.9, 0.6, 0.9),
    "cyan":    (0.6, 0.95, 0.95),
    "gray":    (0.8, 0.8, 0.8),
    "black":   (0.3, 0.3, 0.3),
    "white":   (1, 1, 1),
    "orange":  (0.98, 0.75, 0.55),
    "purple":  (0.75, 0.6, 0.9),
    "pink":    (1, 0.8, 0.85),
    "brown":   (0.75, 0.65, 0.55),
}

class GoogleSheetsManager:
	def __init__(self, credentials_path: str, spreadsheet_id: str, sheet_name: str = None):
		self.credentials_path = credentials_path
		self.spreadsheet_id = spreadsheet_id
		self.sheet_name = sheet_name
		self.client = None
		self.spreadsheet = None
		self.sheet = None

		def authorize_with_Google():
			creds = Credentials.from_service_account_file(self.credentials_path, scopes=[
				"https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
			])
			self.client = gspread.authorize(creds)
			self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
			if self.sheet_name:
				self.sheet = self.spreadsheet.worksheet(self.sheet_name)

		authorize_with_Google()

	def parse(self, coord):
		if ":" in coord:
			coord_range = a1_range_to_grid_range(coord)
			return (coord_range['startRowIndex'] + 1,
					coord_range['startColumnIndex'] + 1,
					coord_range['endRowIndex'],
					coord_range['endColumnIndex'])
		else:
			return a1_to_rowcol(coord)

	def parse_color(self, color_name):
		colors = PASTEL_COLORS
		color_name = color_name.lower()
		if color_name in colors:
			return colors[color_name]
		else:
			raise ValueError(f"Color {color_name} not found, try these: {', '.join(colors.keys())}")

	def cell(self, raw_coord, value = None):
		coord = self.parse(raw_coord)

		# Only one cell
		if isinstance(coord, tuple) and len(coord) == 2:
			row, col = coord
			if value is None:
				return self.sheet.cell(row, col)
			else:		
				return self.sheet.update_cell(row, col, value)

		# Range of cells
		elif isinstance(coord, tuple) and len(coord) == 4:
			row1, col1, row2, col2 = coord
			n_rows = row2 - row1 + 1
			n_cols = col2 - col1 + 1

			if value is None:
				# [1] - If value is None, just read the range
				return self.sheet.get(raw_coord)

			if not isinstance(value, list):
				# [2] - If value is not a list, set the same value for all cells
				value = [[value] * n_cols for _ in range(n_rows)]

			elif isinstance(value, list) and len(value) == n_cols and all(not isinstance(v, list) for v in value):
				# [3] - If value lenght is equal to the number of cols, all rows will have the same values
				value = [value for _ in range(n_rows)]

			elif isinstance(value, list):
				# [4] - If value lenght is not the same of the cols number, won't do anything
				raise ValueError(f"Length of provided values ({len(value)}) does not match number of columns ({n_cols})")
				return

			for r_idx, row in enumerate(value):
				for c_idx, val in enumerate(row):
					self.sheet.update_cell(row1 + r_idx, col1 + c_idx, val)

			return
	def cells(self, raw_coord, value = None):
		self.cell(raw_coord, value)

	def background(self, raw_coord, color):
		r, g, b = self.parse_color(color)
		fmt = CellFormat(backgroundColor = Color(red=r, green=g, blue=b))
		format_cell_range(self.sheet, raw_coord, fmt)
			

	def get_background(self, raw_coord):
		colors = PASTEL_COLORS
		rgb_to_name = {v: k for k, v in colors.items()}
		coord = self.parse(raw_coord)

		# Only one cell
		if isinstance(coord, tuple) and len(coord) == 2:
			row, col = coord
			fmt = get_effective_format(self.sheet, f"{chr(col + 64)}{row}")
			if fmt and fmt.backgroundColor:
				rgb = (
					round(fmt.backgroundColor.red, 2),
					round(fmt.backgroundColor.green, 2),
					round(fmt.backgroundColor.blue, 2)
				)
				return rgb_to_name.get(rgb, "")
			return ""

		# Range of cells
		elif isinstance(coord, tuple) and len(coord) == 4:
			row1, col1, row2, col2 = coord
			results = []
			for r in range(row1, row2 + 1):
				row_colors = []
				for c in range(col1, col2 + 1):
					fmt = get_effective_format(self.sheet, f"{chr(c + 64)}{r}")
					if fmt and fmt.backgroundColor:
						rgb = (
							round(fmt.backgroundColor.red, 2),
							round(fmt.backgroundColor.green, 2),
							round(fmt.backgroundColor.blue, 2)
						)
						row_colors.append(rgb_to_name.get(rgb, ""))
					else:
						row_colors.append("")
				results.append(row_colors)
			return results