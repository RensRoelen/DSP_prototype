import google.generativeai as genai
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD
import re
from collections import Counter

# Define namespaces
EX = Namespace("http://example.org/aec#")
SCHEMA = Namespace("http://schema.org/")


# Read API Key from File
def get_api_key(file_path="api_key.txt"):
    try:
        with open(file_path) as file:
            return file.readline().strip()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        exit(1)

# Configure the Gemini API
def configure_gemini_api(api_key):
    genai.configure(api_key=api_key)

# Generate SPARQL Queries using Gemini LLM with Context Awareness
# Returns multiple potential queries

def generate_sparql_queries(user_query: str, context: dict):
    try:
        model = genai.GenerativeModel("gemini-2.0-flash-exp")

        # Include context in the prompt if available
        context_description = "Context:\n"
        for key in context:
            context_description += f"- {key}: {context[key]}\n"

        prompt = f"""
        You are an expert in generating SPARQL queries for RDF datasets. The dataset uses these properties:
        - `rdfs:label`: A human-readable label for an entity.
        - `ex:address`: The address of a building.
        - `ex:constructionYear`: The year a building was constructed.
        - `ex:architect`: The architect of a building.
        - `ex:totalFloors`: The total number of floors in a building.
        - `ex:hasRoom`: Links a building to its rooms.
        - `ex:hasPermit`: Links a building to its permits.
        - `ex:issuedBy`: The organization that issued a permit.
        - `ex:issueDate`: The date a permit was issued.
        - `ex:expiryDate`: The expiration date of a permit.
        - `ex:approvedUse`: The approved use of a permit.
        - `ex:maxOccupancyGroundFloor`: Maximum occupancy for the ground floor.
        - `ex:maxOccupancyOtherFloors`: Maximum occupancy for other floors.
        - `ex:addition`: Allowed modifications under a permit.
        - `ex:type`: The type of a room.
        - `ex:area`: The area of a room.
        - `ex:hasSteelBeam`: Links a room to its steel beams.
        - `ex:diameter`: The diameter of a steel beam.
        - `ex:material`: The material of a steel beam.

        Prefixes used in the dataset:
        - `@prefix ex: <http://example.org/aec#>`
        - `@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>`
        - `@prefix xsd: <http://www.w3.org/2001/XMLSchema#>`

        {context_description}

        Instructions:
        Generate up to five valid SPARQL queries based on the given question. Return each query separately, with no additional text or annotations.
        
        Question: {user_query}
        SPARQL:
        """
        
        response = model.generate_content(prompt)
        
        # Split response into separate queries using regex to properly handle code blocks
        queries = re.findall(r'```(?:sparql)?\s*(.*?)```', response.text, re.DOTALL)
        
        # Clean each query individually
        sparql_queries = []
        for query in queries:
            cleaned_query = clean_sparql_query(query)
            if any(keyword in cleaned_query.lower() for keyword in ["select", "construct", "describe", "ask"]):
                sparql_queries.append(cleaned_query)
        
        return sparql_queries
    except Exception as e:
        return [f"Error generating SPARQL query: {e}"]

# Clean Up Generated SPARQL Query
def clean_sparql_query(query):
    """
    Cleans up the generated SPARQL query by removing extra whitespace and ensuring consistent formatting.
    """
    # Remove any remaining markdown formatting
    query = query.strip()
    
    # Remove any comments or annotations
    query = re.sub(r'#.*$', '', query, flags=re.MULTILINE)
    
    # Clean up whitespace
    query = ' '.join(query.split())
    
    return query

# Query the RDF Graph with SPARQL
# Also returns a specific error flag or message

def query_graph(graph: Graph, sparql_query: str):
    try:
        results = graph.query(sparql_query)
        output = []
        for row in results:
            output.append(", ".join(str(value) for value in row))
        return "\n".join(output) if output else "No results found."
    except Exception as e:
        return f"Error: {e}"

# Initialize a list to store all interactions
all_interactions = []

# Function to update context with all previous interactions

def update_context_with_interactions():
    context_description = "Context from previous interactions:\n"
    for interaction in all_interactions:
        context_description += f"- {interaction}\n"
    return context_description

# Step 7: Main Function with Context Tracking
if __name__ == "__main__":
    
    print("Welcome to the Natural Language to SPARQL Query Tool!")
    
    # Read API key from file
    api_key = get_api_key()

    # Configure Gemini API with your API key
    configure_gemini_api(api_key)

    print("\nExample Queries:")
    
    print("- 'What is the diameter of Steel Beam 3 in Room X of Building Y?'")


# Main Loop with Enhanced Error Handling
context = {}
retry_flag = False  # Flag to indicate if a retry is requested
