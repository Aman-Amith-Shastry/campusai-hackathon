import requests
from bs4 import BeautifulSoup
import csv
import pandas as pd 

import openai
openai.api_key = "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"


def load_majors_from_csv(csv_file):
    df = pd.read_csv(csv_file)
    majors = df['Title'].tolist()
    return majors

def map_occupation_to_major(occupation_description, majors):
    majors_list = ', '.join(majors) 
    prompt = f"""
    Given the occupation description: '{occupation_description}', 
    suggest the most relevant major from the following list of majors:
    {majors_list}
    """

    response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."}, 
        {"role": "user", "content": f"Given the occupation description: '{occupation_description}', suggest the most relevant major from the following list of majors: {majors_list}"}  # User's input
    ],
    max_tokens=100,
    temperature=0.3
)

    suggested_major = response.choices[0]['message']['content'].strip()
    return suggested_major


def main():

    majors = load_majors_from_csv("Majors.csv") 
    occupation_input = input("Enter the occupation you want to pursue (e.g., Software Engineer, Data Scientist): ")
    major = map_occupation_to_major(occupation_input, majors)
    print(f"Based on the occupation '{occupation_input}', your suggested major is: {major}")

if __name__ == "__main__":
    main()