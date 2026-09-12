class MissingColumns(Exception):
    def __init__(self, col: str):
        super().__init__(col)
