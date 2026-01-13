from fpdf import FPDF

class FlossyPDF(FPDF):
    def header(self):
        # Background Fill
        self.set_fill_color(248, 248, 248)
        self.rect(0, 0, 210, 297, 'F')

        # Background/Margin Decoration
        self.set_draw_color(212, 175, 55) # Gold
        self.set_line_width(0.5)
        self.rect(5, 5, 200, 287) # Subtle border
