import os
import re
import time

import openai
import requests
import stripe
import json
from bs4 import BeautifulSoup
from flask import Flask, redirect
from flask import render_template
from flask import request
from flask import session
from flask_mysqldb import MySQL
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.secret_key = 'mysecretkey'  # para poder usar sesiones

app.config['MYSQL_HOST'] = 'gblm5z.stackhero-network.com'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'NDgFe0m8HhvCbWSEmfzrholpFqLYhbDc'
app.config['MYSQL_DB'] = 'mbot'
app.config['MYSQL_PORT'] = 3306
app.config["MYSQL_CUSTOM_OPTIONS"] = {"ssl": "false"}

mysql = MySQL(app)


@app.route('/')
def index():
    return render_template('sitio/index.html')


@app.route('/services')
def services():
    return render_template('sitio/services.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        textarea = request.form['textarea']
        message = Mail(
            from_email=email,
            to_emails='aniballeguizamobalderas@gmail.com',
            subject=name,
            html_content=textarea
        )
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT sendgrid FROM admin WHERE id = 1")
            data = cur.fetchone()
            cur.close()
            if data is not None:
                sendgrid = data[0]
                sg = SendGridAPIClient(sendgrid)
                response = sg.send(message)
                return render_template('sitio/contact.html', success='Message sent')
        except Exception as e:
            print(e)
            return render_template('sitio/contact.html', error='Message not sent')
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
        # si el usuario existe pero la contraseña no coincide #
        if data is not None and not check_password_hash(data[1], password):
            return render_template('sitio/login.html', error='Wrong password')
        if data is None:
            return render_template('sitio/login.html', error='User not found')
        # si hay datos
        passwordhash = data[1]
        # comparar datos
        if check_password_hash(passwordhash, password):
            session['username'] = username
            session['logged'] = True
            # verificar suscripcion en stripe #
            try:
                cur = mysql.connection.cursor()
                cur.execute("SELECT stripesk FROM admin WHERE id = 1")
                data = cur.fetchone()
                cur.close()
                if data is not None:
                    stripe.api_key = data[0]
                    cur = mysql.connection.cursor()
                    cur.execute("SELECT email FROM users WHERE username = %s", (username,))
                    email = cur.fetchone()
                    cur.close()
                    customer = stripe.Customer.list(email=email[0])['data'][0]
                    subscription = stripe.Subscription.list(customer=customer.id).data[0]
                    if subscription.status == 'active' or subscription.status == 'trialing':
                        return render_template('admin/index.html')
                    else:
                        print(subscription.status)
                        return render_template('sitio/login.html', error='Subscription not active')
            except Exception as e:
                print(e, 'error')
                return render_template('sitio/login.html', error='Subscription not active')
            return render_template('admin/index.html')
    return render_template('sitio/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        # verificar que el usuario no exista #
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        data = cur.fetchone()
        cur.close()
        if data is not None:
            return render_template('sitio/register.html', error='User already registered')
        # verificar que el email no exista #
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        data = cur.fetchone()
        cur.close()
        if data is not None:
            return render_template('sitio/register.html', error='Email already registered')
        password = request.form['password']
        passwordhash = generate_password_hash(password)
        user = {'username': username, 'email': email, 'password': passwordhash}
        # pagar con stripe #
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT stripesk FROM admin WHERE id = 1")
            data = cur.fetchone()
            cur.close()
            if data is not None:
                stripe.api_key = data[0]
                session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price': 'price_1Mp2MHFZwBQ2lPrM4xEUCPs6',
                        'quantity': 1
                    }],
                    mode='suscription',
                    success_url='https://marketbot.herokuapp.com/success' + '?session_id={CHECKOUT_SESSION_ID}',
                    cancel_url='https://marketbot.herokuapp.com/cancel'
                )
                user['session'] = session.id
                cur = mysql.connection.cursor()
                cur.execute("INSERT INTO users2 (username, email, password, stripe_session_id) VALUES (%s, %s, %s, %s)",
                            (username, email, passwordhash, session.id))
                mysql.connection.commit()
                cur.close()
                return redirect(session.url, code=303)
        except Exception as e:
            print(e)
            return render_template('sitio/register.html')
    return render_template('sitio/register.html')


@app.route('/success')
def success():
    cur = mysql.connection.cursor()
    cur.execute("SELECT stripesk FROM admin WHERE id = 1")
    data = cur.fetchone()
    cur.close()
    stripe.api_key = data[0]
    session_id = request.args.get('session_id')
    session = stripe.checkout.Session.retrieve(session_id)
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users2 WHERE stripe_session_id = %s", (session_id,))
    data = cur.fetchone()
    cur.close()
    if data is not None:
        username = data[0]
        email = data[2]
        passwordhash = data[1]
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                    (username, email, passwordhash))
        mysql.connection.commit()
        cur.close()
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM users2 WHERE stripe_session_id = %s", (session_id,))
        mysql.connection.commit()
        cur.close()
        return render_template('sitio/login.html', success='User registered')
    else:
        return render_template('sitio/register.html', error='User not registered')


@app.route('/cancel')
def cancel():
    return render_template('sitio/register.html')


@app.route('/logout')
def logout():
    session.clear()
    return render_template('sitio/index.html')


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'logged' in session:
        username = session['username']
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            textarea = request.form['textarea']
            message = Mail(
                from_email=email,
                to_emails='aniballeguizamobalderas@gmail.com',
                subject=name,
                html_content=textarea
            )
            try:
                cur = mysql.connection.cursor()
                cur.execute("SELECT sendgrid FROM admin WHERE id = 1")
                data = cur.fetchone()
                cur.close()
                sg = SendGridAPIClient(data[0])
                response = sg.send(message)
            except Exception as e:
                print(e)
        return render_template('admin/index.html', username=username)
    return render_template('sitio/index.html')


@app.route('/admin/chatbot', methods=['POST', 'GET'])
def chatbot():
    if request.method == 'GET':
        return render_template('admin/chatbot.html')
    if 'logged' in session:
        username = session['username']
        from_number = 'whatsapp:+528122094187'
    else:
        username = request.form['username']
        from_number = request.form['from_number']
    conversations = []
    if 'conversations' not in session:
        session['conversations'] = []
    if request.form['question']:
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
        cur.execute("SELECT question, answer FROM conversations WHERE username = %s ORDER BY id DESC LIMIT 5",
                    (username,))
        pyr = cur.fetchall()
        cur.close()
        cur = mysql.connection.cursor()
        cur.execute("SELECT db FROM sites WHERE username = %s AND db REGEXP %s ORDER BY id DESC LIMIT 2",
                    (username, '|'.join(questiondb.split())))
        textsite = cur.fetchall()
        cur.close()
        # Convertir a string #
        textsite = str(textsite)
        if textsite == '()':
            textsite = ' '
        # quitar /n y /t #
        textsite = textsite.replace('\\n', ' ')
        textsite = textsite.replace('\\t', ' ')
        # quitar espacios dobles #
        textsite = re.sub(' +', ' ', textsite)
        # quitar palabras de menos de 3 letras #
        textsite = ' '.join([w for w in textsite.split() if len(w) > 3])
        # quitar palabras de mas de 15 letras #
        textsite = ' '.join([w for w in textsite.split() if len(w) < 15])
        # generar pregunta #
        print(textsite)
        prompt = f"{pyr}\n{textsite}\n{question}\n"
        # generar respuesta #
        response = openai.Completion.create(
            model='text-davinci-003',
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
            if api == '':
                return render_template('admin/settings.html', error='Can´t be empty')
            if len(api) < 20:
                return render_template('admin/settings.html', error='The key is too short')
            username = session['username']
            # verificar si ya existe una clave #
            cur = mysql.connection.cursor()
            cur.execute("SELECT openai FROM claves WHERE username = %s ORDER BY id DESC LIMIT 1", (username,))
            data = cur.fetchone()
            cur.close()
            if data is None:
                # guardar clave #
                cur = mysql.connection.cursor()
                cur.execute("INSERT INTO claves (username, openai) VALUES (%s, %s)",
                            (username, api))
                mysql.connection.commit()
                cur.close()
                return render_template('admin/settings.html', success='Key saved')
            if data is not None:
                # actualizar clave #
                cur = mysql.connection.cursor()
                cur.execute("UPDATE claves SET openai = %s WHERE username = %s", (api, username))
                mysql.connection.commit()
                cur.close()
                return render_template('admin/settings.html', success='Key updated')
    return render_template('sitio/index.html')


@app.route('/admin/settings/web', methods=['POST'])
def web():
    if 'logged' in session:
        if request.method == 'POST':
            # verificar que tenga la api en la base de datos #
            username = session['username']
            cur = mysql.connection.cursor()
            cur.execute("SELECT openai FROM claves WHERE username = %s ORDER BY id DESC LIMIT 1", (username,))
            data = cur.fetchone()
            cur.close()
            if data is None:
                return render_template('admin/settings.html', error='The key is not saved')
            # guardar url de la web #
            web = request.form['web']
            if web == '':
                return render_template('admin/settings.html', error='Can´t be empty')
            # verificar si la url es valida #
            try:
                requests.get(web, timeout=5)
            except requests.exceptions.ConnectionError:
                return render_template('admin/settings.html', error='The url is not valid')
            # guardar url en la base de datos #
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
            return render_template('admin/settings.html', success='Url saved')
    return render_template('sitio/index.html')


@app.route('/admin/settings/tw', methods=['POST'])
def tw():
    if 'logged' in session:
        username = session['username']
        # verificar que tenga web en la base de datos #
        cur = mysql.connection.cursor()
        cur.execute("SELECT webpage FROM sites WHERE username = %s ORDER BY id DESC LIMIT 1", (username,))
        data = cur.fetchone()
        cur.close()
        if data is None:
            return render_template('admin/settings.html', error='You need to save a url first')
        tw = request.form['twilio']
        twsk = request.form['twsk']
        numbertw = request.form['numbertw']
        # verificar que los campos no esten vacios #
        if tw == '' or twsk == '' or numbertw == '':
            return render_template('admin/settings.html', error='Can´t be empty')
        # verificar que la clave sea valida #
        try:
            client = Client(tw, twsk)
            client.messages.create(
                to=numbertw,
                from_="+12058585858",
                body="Hola, esto es una prueba de la api de twilio"
            )
        except:
            return render_template('admin/settings.html', error='The key is not valid')
        # guardar clave del usuario en la base de datos #
        cur = mysql.connection.cursor()
        cur.execute("UPDATE claves SET twillio = %s, twsk = %s, numbertw = %s WHERE username = %s",
                    (tw, twsk, numbertw, username))
        mysql.connection.commit()
        cur.close()
        return render_template('admin/settings.html', success='Key saved')
    return render_template('sitio/index.html')


@app.route('/<username>/whatsapp', methods=['POST', 'GET'])
def whatsapp(username):
    # si no existe el usuario no se puede acceder #
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    data = cur.fetchone()
    cur.close()
    if data is None:
        return 'User not found'
    else:
        if request.method == 'POST':
            # obtener datos #
            from_number = request.form['From']
            message = request.form['Body']
            # enviar datos a ulr chatbot #
            url = 'https://marketbot.herokuapp.com/admin/chatbot'
            data = {'question': message, 'from_number': from_number, 'username': username}
            # enviar datos a la url #
            requests.post(url, data=data)
            return 'OK'
        else:
            return 'OK'


@app.route('/admin/posts', methods=['POST', 'GET'])
def posts():
    if 'logged' in session:
        if request.method == 'POST':
            # obtener datos #
            username = session['username']
            titulo = request.form['titulo']
            if titulo == '':
                return render_template('admin/posts.html', error='Can´t be empty')
            if len(titulo) > 100:
                return render_template('admin/posts.html', error='Title too long')
            if len(titulo) < 10:
                return render_template('admin/posts.html', error='Title too short')
            featured_image_url = request.form['featured_image_url']
            if featured_image_url == '':
                return render_template('admin/posts.html', error='Can´t be empty')
            # verificar que la url sea valida #
            try:
                response = requests.get(featured_image_url, timeout=5)
                if response.status_code != 200:
                    return render_template('admin/posts.html', error='The url is not valid')
            except:
                return render_template('admin/posts.html', error='The url is not valid')
            # verificar que los campos no esten vacios #
            if posts == '':
                return render_template('admin/posts.html', error='Can´t be empty')
            # leer key de openai #
            cur = mysql.connection.cursor()
            cur.execute("SELECT openai FROM claves WHERE username = %s ORDER BY id DESC LIMIT 1", (username,))
            key = cur.fetchone()
            cur.close()
            openai.api_key = key[0]
            # leer datos de wordpress #
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM wordpress WHERE username = %s ORDER BY id DESC LIMIT 1", (username,))
            data = cur.fetchone()
            cur.close()
            # verificar que los datos de wordpress no esten vacios #
            sitio = data[3]
            if sitio is None:
                return render_template('admin/posts.html', error='You need to save a wordpress url first')
            loginId = data[1]
            if loginId is None:
                return render_template('admin/posts.html', error='You need to save a wordpress login id first')
            password = data[2]
            if password is None:
                return render_template('admin/posts.html', error='You need to save a wordpress password first')
            # generar prompt #
            prompt = f"{'genera un post con buen SEO para wordpress con el titulo:'}\n{titulo}\n{'con subtitulos, parrafos y palabras importantes'}\n"
            # generar respuesta #
            response = openai.Completion.create(
                model='text-davinci-003',
                prompt=prompt,
                temperature=0.3,
                max_tokens=400,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0.6,
            )
            time.sleep(5)
            # publicar contenido en wordpress #
            response_text = response.choices[0].text
            soup = BeautifulSoup(response_text, 'html.parser')
            title = soup.h1.text
            paragraphs = soup.find_all('p')
            subtitles = soup.find_all('h2')
            content = ""
            for subtitle in subtitles:
                content += f"<h2>{subtitle.text}</h2>"
            for paragraph in paragraphs:
                content += f"<p>{paragraph.text}</p>"
            url = f'{sitio}/wp-json/wp/v2/posts'
            headers = {'Content-Type': 'application/json'}
            payload = {
                'title': title.strip(),
                'content': content.strip(),
                'status': 'publish',
                'featured_media': requests.post(featured_image_url).json().get('id')
            }
            auth = (loginId, password)
            response = requests.post(url, headers=headers, auth=auth, data=json.dumps(payload))
            # si hay error en la web #
            if response.status_code != 201:
                return render_template('admin/posts.html', error='Error publishing post')
            else:
                return render_template('admin/posts.html', success='Post published')
        return render_template('admin/posts.html')
    return render_template('sitio/index.html')


@app.route('/admin/settings/word', methods=['POST'])
def word():
    if 'logged' in session:
        # obtener datos #
        username = session['username']
        sitio = request.form['sitio']
        loginId = request.form['loginId']
        password = request.form['password']
        # verificar que los campos no esten vacios #
        if sitio == '':
            return render_template('admin/settings.html', error='Can´t be empty')
        else:
            # verificar que la url sea valida #
            try:
                response = requests.get(sitio, timeout=5)
                if response.status_code != 200:
                    return render_template('admin/settings.html', error='The url is not valid')
            except:
                return render_template('admin/settings.html', error='The url is not valid')
        if loginId == '':
            return render_template('admin/settings.html', error='Can´t be empty')
        if password == '':
            return render_template('admin/settings.html', error='Can´t be empty')
        # verificar usuario y contraseña #
        url = f'{sitio}/wp-json/wp/v2/posts'
        headers = {'Content-Type': 'application/json'}
        payload = {
            'title': 'test',
            'content': 'test',
            'status': 'publish'
        }
        auth = (loginId, password)
        response = requests.post(url, headers=headers, auth=auth, data=json.dumps(payload))
        if response.status_code != 201:
            return render_template('admin/settings.html', error='Invalid user or password')
        # verificar que no tenga nada en la base de datos #
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM wordpress WHERE username = %s ORDER BY id DESC LIMIT 1", (username,))
        data = cur.fetchone()
        cur.close()
        if data is not None:
            # actualizar datos #
            cur = mysql.connection.cursor()
            cur.execute("UPDATE wordpress SET site = %s, worduser = %s, wordpass = %s WHERE username = %s", (sitio, loginId, password, username))
            mysql.connection.commit()
            cur.close()
            return render_template('admin/settings.html', success='Wordpress updated')
        else:
            # guardar datos #
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO wordpress (username, site, worduser, wordpass) VALUES (%s, %s, %s, %s)", (username, sitio, loginId, password))
            mysql.connection.commit()
            cur.close()
        return render_template('admin/settings.html', success='Wordpress saved')
    return render_template('sitio/index.html')


# obtener puerto #
port = int(os.environ.get('PORT', 8080))
# iniciar servidor #
if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=port)
