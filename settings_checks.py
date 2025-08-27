#settings dict

def prefix(input):
    if len(input) > 1:
        return False
    else:
        return True
def nonnegative_int(input):
    try:
        input = int(input)
        if input >= 0:
            return True
        else:
            return False
    except: return False

def positive_int(input):
    try:
        input = int(input)
        if input > 0:
            return True
        else:
            return False
    except: return False

def percents(input):
    try:
        input = float(input)
        input = input/100
        if input >= 0:
            return True
        else: return False
    except: return False

def onoff(input):
    acceptable = ['on', 'off']
    if str.lower(input) in acceptable:
        return True
    else:
        return False

def numbers(input):
    try:
        return float(input)   # ✅ direkt Zahl zurückgeben
    except:
        raise Exception("Please provide a valid number.")
    
def channel(input):
    if input.startswith('<#') and input.endswith('>') and input[2:-1].isdigit():
        return True
    else:
        return False

def positive_int(input):
    try:
        value = int(input)
        if value <= 0:
            raise Exception("Please provide a positive integer.")
        return value          # ✅ int zurückgeben
    except:
        raise Exception("Please provide a valid positive integer.")


def nonnegative_int(input):
    try:
        value = int(input)
        if value < 0:
            raise Exception("Please provide a non-negative integer.")
        return value          # ✅ int zurückgeben
    except:
        raise Exception("Please provide a valid non-negative integer.")


def numberlist(arg):
    try:
        numbers = [int(x.strip()) for x in arg.split(",")]
        for n in numbers:
            if n < 0:
                raise Exception("Numbers must be non-negative")
        return numbers        # ✅ Liste von ints zurückgeben
    except:
        raise Exception("Please provide a list of non-negative integers separated by commas.")
