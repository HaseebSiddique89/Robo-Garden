import requests
import json
from pyaiml21 import Kernel
from glob import glob
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from py2neo import Graph, Node, Relationship

def get_sensor_data():
    url = "http://172.20.10.2/sensors"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.RequestException as e:
        print(f"Error requesting sensor data: {e}")
        return None

def update_aiml_variables(kernel, sensor_data):
    if sensor_data:
        kernel.setPredicate("temperature", str(sensor_data['temperature']), "USER_1")
        kernel.setPredicate("humidity", str(sensor_data['humidity']), "USER_1")
        kernel.setPredicate("air_quality", sensor_data['air_quality'], "USER_1")
        kernel.setPredicate("moisture", str(sensor_data['moisture']), "USER_1")
        
        gases = ["Carbon Dioxide", "Carbon Monoxide", "Ammonia", "Nitrogen Dioxide"]
        
        for gas in gases:
            quality = sensor_data['gas_concentrations'][gas][0]
            kernel.setPredicate(gas.lower().replace(" ", "_") + "_quality", quality, "USER_1")

def update_sensor_nodes(sensor_data):
    if sensor_data:
        dht11_node = graph.nodes.match("sensor", name='DHT11', user_id=current_user_id).first()
        mq135_node = graph.nodes.match("sensor", name='MQ135', user_id=current_user_id).first()
        moisture_node = graph.nodes.match("sensor", name='Moisture', user_id=current_user_id).first()

        if dht11_node:
            dht11_node['Temperature'] = str(sensor_data['temperature'])
            dht11_node['Humidity'] = str(sensor_data['humidity'])
            graph.push(dht11_node)
        
        if mq135_node:
            mq135_node['Air_Quality'] = sensor_data['air_quality']
            for gas in ["Carbon Dioxide", "Carbon Monoxide", "Ammonia", "Nitrogen Dioxide"]:
                quality = sensor_data['gas_concentrations'][gas][0]
                mq135_node[gas.replace(" ", "_")] = quality
            graph.push(mq135_node)

        if moisture_node:
            moisture_node['Moisture_Level'] = str(sensor_data['moisture'])
            graph.push(moisture_node)

# Initialize AIML kernel
k = Kernel()

# Learn AIML files
aiml_files = glob('D://Studies//6th Semester//Knowledge Representation & Reasoning//Project//aiml//*.aiml')
for file_path in aiml_files:
    k.learn(file_path)

# Initialize Flask app
app = Flask(__name__)
graph = Graph("bolt://localhost:7687", auth=("neo4j", "12345678"))

current_user_id = None
current_episode_id = None

app.secret_key = 'naming'
        
def reset_variable():
    k.setPredicate("relation", "", "USER_1")
    k.setPredicate("myrel", "" , "USER_1")
    k.setPredicate("person", "", "USER_1")
    k.setPredicate("person1", "", "USER_1")
    k.setPredicate("person2", "", "USER_1")
    k.setPredicate("friend", "", "USER_1")

    
def get_variables():
    # Retrieve predicates and print them for debugging
    relation = k.getPredicate("relation", "USER_1")
    myrel = k.getPredicate("myrel", "USER_1")
    person = k.getPredicate("person", "USER_1")
    person1 = k.getPredicate("person1", "USER_1")
    person2 = k.getPredicate("person2", "USER_1")
    friend = k.getPredicate("friend", "USER_1")
    
    print("################################################")
    print("In get_variables")
    print("relation:", relation)
    print("myrel:", myrel)
    print("person:", person)
    print("person1:", person1)
    print("person2:", person2)
    print("friend:", friend)
    print("################################################")

    # Store retrieved predicates in a dictionary
    My_Dict = {
        "relation": relation,
        "myrel": myrel,
        "person": person,
        "person1": person1,
        "person2": person2,
        "friend": friend
    }
    create_nodes_relations(My_Dict)


def create_nodes_relations(My_Dict):
    social_node = graph.nodes.match("Social", user_id=current_user_id).first()

    non_empty_keys = [key for key, value in My_Dict.items() if value]
    # print("Keys with non-empty values:", non_empty_keys)

    if not social_node:
        print("Current user's social node not found")
        return

    
    elif "relation" in non_empty_keys and "person" in non_empty_keys:

        relation = My_Dict["relation"]
        person = My_Dict["person"]
        print("################################################")
        print(relation, person)
        print("################################################")
        person_node = Node('Person', name=person)
        graph.merge(person_node, 'Person', "name")

        graph.merge(Relationship(social_node, relation, person_node))
        

        reset_variable()

    elif "person1" in non_empty_keys and "relation" in non_empty_keys and "person2" in non_empty_keys:
        person1 = My_Dict["person1"]
        relation = My_Dict["relation"]
        person2 = My_Dict["person2"]

        # properties = {"name": person1}
        parent_node = Node("Person", name=person1)
        graph.merge(parent_node, "Person", "name")

        child_node = Node("Person", name=person2)
        graph.merge(child_node, "Person", "name")

        relationship = Relationship(parent_node, relation, child_node)
        graph.merge(relationship)

        reset_variable()

    elif "myrel" in non_empty_keys:
        myrel = My_Dict["myrel"]

        query = f"""
        MATCH (social:Social {{user_id: {current_user_id}}})-[:{myrel}]->(person:Person)
        RETURN person
        """

        result = graph.run(query)

        names = [record["person"]["name"] for record in result]
        print("##################################")
        print("Names: ", names)
        names_string = ", ".join(names)

        try:
            k.setPredicate("friend", names_string, "USER_1")
            print("Predicate 'friend' set successfully.")
        except Exception as e:
            print("Error setting predicate 'friend':", str(e))

        # reset_variable()


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    user_node = graph.nodes.match("User", email=email).first()
    if user_node:
        return "Already Registered!"
    else:
        user_node = Node("User", name=name, email=email, password=password)
        graph.create(user_node)

        k.respond("Hello", "USER_1")
        k.setPredicate('username', name, "USER_1")
        
        episodic_node = Node("Episodic", name="Episodic", user_id=user_node.identity)
        sensory_node = Node("Sensory", name="Sensory", user_id=user_node.identity)
        semantic_node = Node("Semantic", name="Semantic", user_id=user_node.identity)
        episode_node = Node("Episode", name="episode1", user_id=user_node.identity)
        social_node = Node("Social", name="Social", user_id=user_node.identity)

        # Create sensor nodes and relationships
        dht11_node = Node("sensor", name="DHT11", user_id=user_node.identity, Temperature="0", Humidity="0")
        mq135_node = Node("sensor", name="MQ135", user_id=user_node.identity, Air_Quality="0", Carbon_Dioxide="0", Carbon_Monoxide="0", Ammonia="0", Nitrogen_Dioxide="0")
        moisture_node = Node("sensor", name="Moisture", user_id=user_node.identity, Moisture_Level="0")
        
        graph.create(episodic_node)
        graph.create(sensory_node)
        graph.create(semantic_node)
        graph.create(episode_node)
        graph.create(social_node)

        graph.create(dht11_node)
        graph.create(mq135_node)
        graph.create(moisture_node)

        graph.create(Relationship(user_node, "HAS", episodic_node))
        graph.create(Relationship(user_node, "HAS", sensory_node))
        graph.create(Relationship(user_node, "HAS", semantic_node))
        graph.create(Relationship(user_node, "HAS", social_node))
        graph.create(Relationship(episodic_node, "STARTS", episode_node))
        
        graph.create(Relationship(sensory_node, "CONTAINS", dht11_node))
        graph.create(Relationship(sensory_node, "CONTAINS", mq135_node))
        graph.create(Relationship(sensory_node, "CONTAINS", moisture_node))
        
        global current_user_id 
        global current_episode_id
        current_user_id = user_node.identity
        current_episode_id = episode_node.identity
        
        session['user_name'] = name

        return redirect(url_for('chat'))

@app.route('/signin', methods=['POST'])
def signin():
    email = request.form['email']
    password = request.form['password']
    user_node = graph.nodes.match("User", email=email, password=password).first()
    if user_node:
        k.respond('Hi', "USER_1")
        name = user_node['name']
        k.setPredicate('username', name, "USER_1")

        global current_user_id
        current_user_id = user_node.identity
        global current_episode_id

        episodic_node = graph.nodes.match("Episodic", user_id=current_user_id).first()
        episode_count = len(list(graph.relationships.match((episodic_node,), r_type="STARTS")))
        new_episode_name = f"episode{episode_count + 1}"
        new_episode_node = Node("Episode", name=new_episode_name, user_id=current_user_id)
        
        # print("################################", current_episode_id)
        graph.create(new_episode_node)
        current_episode_id = new_episode_node.identity
        graph.create(Relationship(episodic_node, "STARTS", new_episode_node))
        
        session['user_name'] = name

        return redirect(url_for('chat'))
    else:
        return "Don't Have an account! Register yourself first"

@app.route('/chat')
def chat():
    user_name = session.get('user_name', 'User')
    return render_template('chat.html', user_name=user_name)

@app.route('/get_response', methods=['POST'])
def get_response():
    k.respond('Hi', "USER_1")
    user_input = request.json.get("message")
    sensor_data = get_sensor_data()
    if sensor_data:
        update_aiml_variables(k, sensor_data)
        update_sensor_nodes(sensor_data)
    response = k.respond(user_input, "USER_1")
    get_variables()

    # Fetch the current episode node
    episode_node = graph.nodes.get(current_episode_id)
    
    # Load existing chats or initialize an empty dictionary
    if 'chats' in episode_node:
        chats = json.loads(episode_node['chats'])
    else:
        chats = {}

    # Determine the new prompt key
    prompt_count = len(chats)
    new_prompt = f"prompt{prompt_count + 1}"

    # Add the new user-bot interaction to the chats dictionary
    chats[new_prompt] = {"user": user_input, "bot": response}

    # Serialize the chats dictionary to a JSON string and update the node
    episode_node['chats'] = json.dumps(chats)
    graph.push(episode_node)
    
    return jsonify({"response": response})

if __name__ == '__main__':
    app.run(debug=True, port=5001)
