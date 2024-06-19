class FileUploadFailed(Exception):
    def __init__(self, file: str | None = None):
        super().__init__(f"File {file} could not be uploaded")
