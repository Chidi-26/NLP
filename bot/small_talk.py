import random
# A dictionary mapping common small talk phrases to possible responses.
responses = {
        "how are you": ["I'm doing well, thanks for asking!", "I'm doing great!","I'm fine thanks!", "All good here!, how may I help you?"],
        "thanks": ["You're welcome!", "No problem! Always happy to help.","Anytime!"],
        "thank you": ["You're welcome!", "No problem! Always happy to help."],
        "what's the weather like": ["I don't have access to real time weather data, but I hope it's nice where you are!"],
        
    }

# This function detects small talk phrases and generates a random appropriate response.
def small_talk(user_txt: str) -> str:

    #Convert text to lower case and strip whitespace for easier matching
    user_input_lower = user_txt.lower().strip() 
    #Loop through each small talk key word in 'responses'
    for key, replies in responses.items():
        #If keyword exsists in user_txt return a random pre-written reply
        if key in user_input_lower:
            return random.choice(replies)
    #If nothing matches return None
    return None