import re
from typing import List
from nltk.tokenize import RegexpTokenizer
from nltk.stem import PorterStemmer
from nltk.corpus import stopwords

# Load English stopwords
sw = set(stopwords.words('english')) 
#Initialize Porter Stemmer for reducing words to their root form
stemer = PorterStemmer()
#Initialize tokenizer to extract words only
tokenizer = RegexpTokenizer(r'[A-Za-z]+')

# This function tokenizes and stems the input text, removes stopwords, and returns list of stemmed tokens
def tokenize_and_stem(user_txt: str) -> List[str]:
    # Convert text to lower case and tokenize
    tokens = tokenizer.tokenize(user_txt.lower())
    # Stem tokens and filter out stopwords
    filtered_tokens = [stemer.stem(token) for token in tokens if token not in sw]
    return filtered_tokens

# This function normalises the input text by lowercasing, removing non-alphanumeric characters, and stemming
def normalise_text(user_txt: str) -> str:
    # Convert text to lower case 
    user_txt = user_txt.lower()
    # Remove non-alphanumeric characters
    user_txt = re.sub(r'[^a-zA-Z0-9\s]', '', user_txt)
    return " ".join(tokenize_and_stem(user_txt))