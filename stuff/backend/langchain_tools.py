import re
import requests
from langchain.tools import BaseTool
from langchain_core.tools import create_retriever_tool
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
# from langchain_openai import OpenAIEmbeddings
from sentence_transformers import SentenceTransformer

# SOC API setup
API_BASE = "https://api-gw.it.umich.edu/Curriculum/SOC"
HEADERS = {
    "Authorization": "Bearer 2yAzQGAbwLunmpKHZtkSAlbXwQzN",
    "Accept": "application/json"
}

# Example term
TERM = "2610"  # replace with desired term code

"""Course search tool that queries UMich's SOC API based on keywords extracted from user input."""
def parse_keywords(prompt: str):
    """
    Simple keyword extractor: lowercase words of 3+ letters
    Can be replaced with more advanced NLP if needed
    """
    words = re.findall(r"\b[a-zA-Z]{3,}\b", prompt.lower())
    return list(set(words))


def query_soc(school_code: str, subject: str):
    """Fetch course details from SOC API for a given subject code"""
    url = f"{API_BASE}/Terms/{TERM}/Schools/{school_code}/Subjects/{subject}/CatalogNbrs"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    if not data.get("Classes"):
        return None
    courses = data["getSOCCtlgNbrsResponse"]["ClassOffered"]
    return courses  # return first course as example


def search_courses_by_keywords(keywords, max_results=5):
    """
    Search courses by matching keywords to course descriptions
    """
    results = []


    for subj in subjects:
        for num in catalog_numbers:
            try:
                course = query_soc(subj, str(num))
                if course:
                    description = course["description"].lower()
                    print(description)
                    if any(k in description for k in keywords):
                        results.append(course)
                        if len(results) >= max_results:
                            return results
            except Exception:
                continue
    return results


class SearchCoursesTool(BaseTool):
    name: str = "search_courses"
    description: str = (
        "Search UMich courses based on keywords extracted from user "
        "input query; returns up to 5 relevant courses."
    )

    def _run(self, query: str):
        keywords = parse_keywords(query)
        courses = search_courses_by_keywords(keywords)
        if not courses:
            return "No relevant courses found."
        return "\n".join(
            f"{c['course']}: {c['title']} — {c['description'][:200]}..."
            for c in courses
        )

    async def _arun(self, query: str):
        raise NotImplementedError("Async not supported in this tool.")
    

class GetCourseDetailTool(BaseTool):
    name: str = "get_course_detail"
    description: str = (
        "Get a detailed course description from the SOC API "
        "given a subject and catalog number. "
        "Input should be of the format '<SUBJECT> <CATALOG_NUMBER>'."
    )

    def _run(self, query: str):
        # parse subject and number
        parts = query.strip().split()
        if len(parts) != 2:
            return "Please provide input like 'EECS 216'."

        subject, catalog = parts
        try:
            # first, find matching class numbers via search
            search_url = f"{API_BASE}/Terms/{TERM}/ClassSearch"
            params = {"Subject": subject.upper(), "CourseNumber": catalog}
            r = requests.get(search_url, headers=HEADERS, params=params)
            r.raise_for_status()
            data = r.json()

            # if no classes found
            class_list = data.get("Classes")
            if not class_list:
                return f"No matches found for {subject} {catalog} in term {TERM}."

            # pick first class match
            class_number = class_list[0]["ClassNumber"]

            # now fetch details
            detail_url = f"{API_BASE}/Terms/{TERM}/Classes/{class_number}/CombinedSections"
            r2 = requests.get(detail_url, headers=HEADERS)
            r2.raise_for_status()
            details = r2.json()

            # extract description
            desc = details.get("Description") or details.get("description")
            title = details.get("CourseTitle") or details.get("courseTitle")

            return (
                f"{subject.upper()} {catalog} — {title}\n"
                f"{desc}"
            )

        except Exception as e:
            return f"Error fetching course detail: {str(e)}"

    async def _arun(self, query: str):
        raise NotImplementedError("Async not supported.")


"""RAG Tool to query major requirements."""

# Connect to your Qdrant server
qdrant_client = QdrantClient(
    url="http://localhost:6333",
    prefer_grpc=True
)

def retrieve_major_info(major: str, qdrant_client, embedder):
    queries = [
        f"{major} prerequisites",
        f"{major} declaration requirements",
        f"{major} core requirements",
        f"{major} upper level requirements",
        # f"{major} systems courses",
        # f"{major} networking courses",
        f"{major} graduation requirements",
    ]
    chunks = []
    seen = set()
    for q in queries:
        qvec = embedder.encode(q).tolist()
        results = qdrant_client.query_points(
            collection_name="hackathon_docs",
            query=qvec,
            limit=5,
            with_payload=True,
        )
        for r in results.points:
            text = r.payload.get("text", "").strip()
            if text and text not in seen:
                seen.add(text)
                chunks.append({
                    "query": q,
                    "score": float(r.score),
                    "text": text,
                    "major": r.payload.get("major", "")
                })
    return chunks


class RetrieveMajorInfoTool(BaseTool):
    name: str = "retrieve_major_info"
    description: str = (
        "Retrieve relevant major requirement information from the vector store. "
        "Input should be the name of the major (e.g., 'Computer Science')."
    )

    def _run(self, major: str):
        embedder = SentenceTransformer("all-MiniLM-L6-v2")
        results = retrieve_major_info(major, qdrant_client, embedder)
        if not results:
            return f"No information found for {major}."
        return "\n\n".join(
            f"Query: {r['query']}\nScore: {r['score']:.4f}\nText: {r['text'][:300]}..."
            for r in results
        )

    async def _arun(self, major: str):
        raise NotImplementedError("Async not supported in this tool.")

# llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

# tools = [SearchCoursesTool()]

# agent = agent = create_agent(
#     model=llm,
#     tools=tools,
#     system_prompt="You are a helpful AI that can search courses.",
# )

# prompt = "I'm interested in machine learning."
# response = agent.invoke(
#     {"messages": [{"role": "user", "content": prompt}]}
# )
# print(response)