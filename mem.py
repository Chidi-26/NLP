# global variable to store username
USERNAME = 'traveller ' # used traveller as a placeholder username

# sets username
def set_username(name: str) -> None:
    global USERNAME
    # strip username of leadiing white spaces
    USERNAME = name.strip() 

# gets username
def get_username() -> str:
    return USERNAME
    