import openai
import os
import requests
from flask import Flask
from flask import render_template
from flask_mysqldb import MySQL
from MySQLdb import _mysql
from flask import session
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from flask import request
from bs4 import BeautifulSoup
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = 'mysecretkey'  # para poder usar sesiones

app.config['MYSQL_HOST'] = 'gblm5z.stackhero-network.com'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'NDgFe0m8HhvCbWSEmfzrholpFqLYhbDc'
app.config['MYSQL_DB'] = 'mbot'

mysql = MySQL(app)


@app.route('/')
def index():
    return render_template('sitio/index.html')


@app.route('/about')
def about():
    return render_template('sitio/about.html')


@app.route('/services')
def services():
    return render_template('sitio/services.html')


@app.route('/contact')
def contact():
    return render_template('sitio/contact.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # traer datos de la base de datos para comparar
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        data = cur.fetchone()
        cur.close()
        # si no hay datos
        if data is None:
            return render_template('sitio/login.html')
        # si hay datos
        passwordhash = data[1]
        # comparar datos
        if check_password_hash(passwordhash, password):
            session['username'] = username
            session['logged'] = True
            return render_template('admin/index.html')
    return render_template('sitio/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        passwordhash = generate_password_hash(password)
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                    (username, email, passwordhash))
        mysql.connection.commit()
        cur.close()
        return render_template('sitio/login.html')
    return render_template('sitio/register.html')


@app.route('/logout')
def logout():
    session.clear()
    return render_template('sitio/index.html')


@app.route('/admin')
def admin():
    if 'logged' in session:
        return render_template('admin/index.html')
    return render_template('sitio/index.html')


@app.route('/admin/chatbot', methods=['POST', 'GET'])
def chatbot():
    if request.method == 'GET':
        return render_template('admin/chatbot.html')
    conversations = []
    if 'conversations' not in session:
        session['conversations'] = []
    if request.form['question']:
        username = request.form['username']
        from_number = request.form['from_number']
        question = 'User: ' + request.form['question']
        questiondb = request.form['question']
        # leer key de openai #
        cur = mysql.connection.cursor()
        cur.execute("SELECT openai FROM claves WHERE username = %s ORDER BY id DESC LIMIT 1", (username,))
        key = cur.fetchone()
        cur.close()
        openai.api_key = key[0]
        # leer ultimas preguntas y respuestas #
        cur = mysql.connection.cursor()
        cur.execute("SELECT question, answer FROM conversations WHERE username = %s ORDER BY id DESC LIMIT 10",
                    (username,))
        pyr = cur.fetchall()
        cur.close()
        # traer solo los row de el usuario que contenga la palabra clave #
        cur = mysql.connection.cursor()
        cur.execute("SELECT db FROM sites WHERE username = %s", (username,))
        textsite = cur.fetchall()
        cur.close()
        # convertir a string #
        textsite = str(textsite)
        # quitar /n y /t #
        textsite = textsite.replace('\\n', ' ')
        # quitar caracteres especiales #
        textsite = textsite.replace('\\t', ' ')
        textsite = textsite.replace('\\', '')
        textsite = textsite.replace('(', '')
        textsite = textsite.replace(')', '')
        textsite = textsite.replace(',', '')
        textsite = textsite.replace("'", '')
        textsite = textsite.replace('[', '')
        textsite = textsite.replace(']', '')
        # dejar 1 espacio entre palabras #
        textsite = ' '.join(textsite.split())
        # eliminar palabras iguales #
        textsite = ' '.join(dict.fromkeys(textsite.split()))
        # generar pregunta #
        prompt = f"{pyr}\n{textsite}\n{question}\n"
        # generar respuesta #
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            temperature=0.3,
            max_tokens=150,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0.6,
        )
        answer = response['choices'][0]['text']
        conversations.append(question)
        conversations.append(answer)
        # enviar mensaje #
        cur = mysql.connection.cursor()
        cur.execute("SELECT twillio FROM claves WHERE username = %s ORDER BY id DESC LIMIT 1", (username,))
        data = cur.fetchone()
        cur.close()
        account_sid = data[0]
        cur = mysql.connection.cursor()
        cur.execute("SELECT twsk FROM claves WHERE username = %s ORDER BY id DESC LIMIT 1", (username,))
        data = cur.fetchone()
        cur.close()
        auth_token = data[0]
        cur = mysql.connection.cursor()
        cur.execute("SELECT numbertw FROM claves WHERE username = %s ORDER BY id DESC LIMIT 1", (username,))
        data = cur.fetchone()
        cur.close()
        numbertw = data[0]
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            from_=numbertw,
            body=answer,
            to=from_number
        )
        # guardar preguntas y respuestas de el usuario #
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO conversations (username, question, answer) VALUES (%s, %s, %s)",
                    (username, questiondb, answer))
        mysql.connection.commit()
        cur.close()
        return render_template('admin/chatbot.html', chat=conversations, answer=answer)
    else:
        return render_template('admin/index.html')


@app.route('/admin/settings', methods=['GET'])
def settings():
    if 'logged' in session:
        return render_template('admin/settings.html')
    return render_template('sitio/index.html')


@app.route('/admin/settings/api', methods=['POST'])
def key():
    if 'logged' in session:
        if request.method == 'POST':
            api = request.form['api']
            username = session['username']
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO claves (username, openai) VALUES (%s, %s)",
                        (username, api))
            mysql.connection.commit()
            cur.close()
            return render_template('admin/settings.html')
    return render_template('sitio/index.html')


@app.route('/admin/settings/web', methods=['POST'])
def web():
    if 'logged' in session:
        if request.method == 'POST':
            web = request.form['web']
            username = session['username']
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO sites (username, webpage) VALUES (%s, %s)",
                        (username, web))
            mysql.connection.commit()
            cur.close()
            # leer url de la web #
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM sites WHERE username = %s ORDER BY id DESC LIMIT 1", (username,))
            data = cur.fetchone()
            cur.close()
            url = data[0]
            # leer contenido de la web #
            page = requests.get(url, timeout=5)
            soup = BeautifulSoup(page.content, 'html.parser')
            # Obtener todas las URLs en la página web
            urls = [url]
            for link in soup.find_all('a'):
                href = link.get('href')
                if href is not None:
                    if href.startswith('http'):
                        urls.append(href)
                    else:
                        url_parts = url.split('/')
                        base_url = url_parts[0] + '//' + url_parts[2] + '/'
                        full_url = base_url + href
                        urls.append(full_url)

            # Leer el texto de cada URL
            for url in urls:
                response = requests.get(url, timeout=5)
                text = BeautifulSoup(response.content, 'html.parser').get_text()

                # guardar texto de la web #
                cur = mysql.connection.cursor()
                cur.execute("INSERT INTO sites (username, webpage, db) VALUES (%s, %s, %s)",
                            (username, web, text))
                mysql.connection.commit()
                cur.close()
                # si hay error en la web #
                if response.status_code != 200:
                    return render_template('admin/settings.html')
            return render_template('admin/settings.html')
    return render_template('sitio/index.html')


@app.route('/admin/settings/tw', methods=['POST'])
def tw():
    if 'logged' in session:
        tw = request.form['twilio']
        username = session['username']
        twsk = request.form['twsk']
        numbertw = request.form['numbertw']
        # guardar clave del usuario en la base de datos #
        cur = mysql.connection.cursor()
        cur.execute("UPDATE claves SET twillio = %s, twsk = %s, numbertw = %s WHERE username = %s",
                    (tw, twsk, numbertw, username))
        mysql.connection.commit()
        cur.close()
        return render_template('admin/settings.html')
    return render_template('sitio/index.html')


@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    from_number = request.form['From']
    message = request.form['Body']
    username = session['username']
    # enviar datos a ulr chatbot #
    url = 'https://marketbot.herokuapp.com/admin/chatbot'
    data = {'question': message, 'from_number': from_number, 'username': username}
    # enviar datos a la url #
    requests.post(url, data=data)
    return 'OK'


# obtener puerto #
port = int(os.environ.get('PORT', 8080))
# iniciar servidor #
if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=port)
