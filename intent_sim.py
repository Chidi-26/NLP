# Imports
import os, json
import numpy as np
from collections import defaultdict
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.metrics.pairwise import cosine_similarity
from bot.preprocessing import normalise_text


#Path to json intent file
dataIntents = os.path.join(os.path.dirname(__file__),"..","data", "intents.json")

# Intent Matcher Class
class SimularityIntentMatcher:

    MIN_CONFIDENCE = 0.20
    
    # Constructor initialisation
    def __init__(self):
        # Initialize vectorizer and TF-IDF transformer
        self.vectorizer = CountVectorizer()
        self.tfid = TfidfTransformer(use_idf= True, sublinear_tf= True)
        
        # holds list of intent labels
        self.labels: list[str] = []
        
        # holds centroid vector for each intent label
        self.centroids = None
        
        
    # Build TF-IDF represatation and compute centroid for each intent label
    def fit(self): 
        # Load intent data from JSON file
        with open(dataIntents, "r", encoding= "utf-8") as f:
            raw = json.load(f)
        
        # Store all utterances and their corresponding labels
        texts, y = [], [] 
        #fixes ordering for consistent indexing
        self.labels = sorted(raw.keys()) 
        #Dictionary to hold list of vectors for each label
        lblToVec = defaultdict(list)
        
        #Build raw text curpus and label list
        for labels, utterances in raw.items():
            for u in utterances:
                #apply text normalization
                normUtt = normalise_text(u)
                texts.append(normUtt)
                y.append(labels)
                
        
        #Vectorise corpus and compute TF-IDF
        X_counts = self.vectorizer.fit_transform(texts)
        X_tfidf = self.tfid.fit_transform(X_counts)

        # Group TF-IDF vectors by their labels
        for i, label in enumerate(y):
            rowVec = X_tfidf[i]                     
            lblToVec[label].append(rowVec.toarray()[0])

        # Compute centroid for each label
        centroids = []

        # For each label, compute the centroid of its vectors
        for label in self.labels:
            vecs = lblToVec[label]
            if vecs:
                mat = np.vstack(vecs)               
                centroid = np.mean(mat, axis=0) 
                centroids.append(centroid)

            # Handle case with no vectors for a label
            else:
                centroids.append(np.zeros((X_tfidf.shape[1],), dtype=float))

        # Stack centroids into a matrix
        self.centroids = np.vstack(centroids)
        
    # Return the trained model
    def predictScore(self, text: str) -> tuple[str, float]:
        # Transform input text to TF-IDF vector
        v = self.tfid.transform(self.vectorizer.transform([normalise_text(text)]))
        # Compute cosine similarity between input vector and centroids
        sims = cosine_similarity(v, self.centroids)[0]
        # Identify the label with the highest similarity score
        bestIdx = int(np.argmax(sims))
        # Return the best matching label and its similarity score
        return self.labels[bestIdx], float(sims[bestIdx])
        
    # Predict intent label for given text
    def predict(self, text: str) -> str:
        # Gets the predicted label and its score
        label, score = self.predictScore(text)
        # If score is below minimum confidence, return 'unknown' intent
        if score < self.MIN_CONFIDENCE:
            return 'unknown'

        # return the label
        return label
            
        