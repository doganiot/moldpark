from django.core.exceptions import ValidationError

def validate_file_size(value):
    filesize = value.size
    
    if filesize > 52428800:  # 50MB
        raise ValidationError("Maksimum dosya boyutu 50MB olabilir.")
    else:
        return value 