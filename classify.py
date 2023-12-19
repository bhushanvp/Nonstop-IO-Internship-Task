import os
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, classification_report
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

csv_file = "./scraped_data/article_data.csv"
base_folder = "./scraped_data"

df = pd.read_csv(csv_file)

file_names = df['File_Name'].tolist()
labels = df['Section'].tolist()

data = []
filtered_labels = []
filtered_filenames = []

for file_name, label in zip(file_names, labels):
    file_path = os.path.join(base_folder, file_name)

    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            text_content = file.read()
            data.append(text_content)
            filtered_labels.append(label)
            filtered_filenames.append(file_name)

class_counts = pd.Series(filtered_labels).value_counts().to_dict()

labels = filtered_labels

file_data_df = pd.DataFrame({'File_Name': filtered_filenames, 'Text': data})

df_train, df_test, y_train, y_test = train_test_split(file_data_df, labels, test_size=0.2, random_state=42)

X_train = df_train.drop('File_Name', axis=1)['Text']
X_test = df_test.drop('File_Name', axis=1)['Text']

vectorizer = CountVectorizer(stop_words=list(ENGLISH_STOP_WORDS))
X_train_vectorized = vectorizer.fit_transform(X_train)
X_test_vectorized = vectorizer.transform(X_test)

classifier = MultinomialNB()
classifier.fit(X_train_vectorized, y_train)

predictions = classifier.predict(X_test_vectorized)

results_df = pd.DataFrame({
    'File_Name': df_test['File_Name'],
    'Actual_Label': y_test,
    'Predicted_Label': predictions
})

if not os.path.exists('results/'):
    os.mkdir('results')

results_csv = 'results/classification_results.csv'
results_df.to_csv(results_csv, index=False)

print("Results DataFrame:")
print(results_df)

accuracy = accuracy_score(y_test, predictions)
print(f"\nAccuracy: {accuracy:.2f}")

print("\nClassification Report:")
print(classification_report(y_test, predictions))
