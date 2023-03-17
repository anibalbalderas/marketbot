// cambiar color de a si estoy en esa pagina //
const menu = document.querySelectorAll('.menu__link');
const url = window.location.href;

menu.forEach((item) => {
  if (item.href === url) {
    item.classList.add('menu__link--active');
  }
});

// validar registro //
const form = document.getElementById('form');
const name = document.getElementById('username');
const email = document.getElementById('email');
const password = document.getElementById('password');
const password2 = document.getElementById('password2');

// si hay un submit //
if (form) {
  form.addEventListener('submit', (e) => {
    e.preventDefault();

    checkInputs();
  });
}

function checkInputs() {
    const nameValue = name.value.trim();
    const emailValue = email.value.trim();
    const passwordValue = password.value.trim();
    const password2Value = password2.value.trim();

    if(nameValue === '') {
        setErrorFor(name, 'El nombre no puede estar vacio');
    } else {
        setSuccessFor(name);
    }

    if(emailValue === '') {
        setErrorFor(email, 'El email no puede estar vacio');
    } else if (!isEmail(emailValue)) {
        setErrorFor(email, 'No es un email valido');
    } else {
        setSuccessFor(email);
    }

    if(passwordValue === '') {
        setErrorFor(password, 'La contraseña no puede estar vacia');
    } else if (passwordValue.length < 8) {
        setErrorFor(password, 'La contraseña debe tener al menos 8 caracteres');
    } else{
        setSuccessFor(password);
    }

    if(password2Value === '') {
        setErrorFor(password2, 'La contraseña no puede estar vacia');
    } else if(passwordValue !== password2Value) {
        setErrorFor(password2, 'Las contraseñas no coinciden');
    } else{
        setSuccessFor(password2);
    }
}

function setErrorFor(input, message) {
    const formControl = input.parentElement;
    const small = formControl.querySelector('small');

    small.innerText = message;
}

function setSuccessFor() {
    // enviar formulario si todos los campos estan bien //
    if (name.value !== '' && email.value !== '' && password.value !== '' && password2.value !== '' && password.value.length >= 8 && password.value === password2.value) {
        form.submit();
    }
}

function isEmail(email) {
    return /^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$/.test(email);
}

const small = document.querySelectorAll('small');

if (form) {
    form.addEventListener('click', () => {
        small.forEach((item) => {
            item.innerText = '';
        });
    });
}

// validar login //
const formLogin = document.getElementById('form');
const usernameLogin = document.getElementById('username-l');
const passwordLogin = document.getElementById('password-l');

// si hay un submit //
if (formLogin) {
    formLogin.addEventListener('submit', (e) => {
        e.preventDefault();

        checkInputsLogin();
    });
}

function checkInputsLogin() {
    const usernameLoginValue = usernameLogin.value.trim();
    const passwordLoginValue = passwordLogin.value.trim();

    if(usernameLoginValue === '') {
        setErrorForLogin(usernameLogin, 'El nombre no puede estar vacio');
    } else {
        setSuccessForLogin(usernameLogin);
    }

    if(passwordLoginValue === '') {
        setErrorForLogin(passwordLogin, 'La contraseña no puede estar vacia');
    } else if (passwordLoginValue.length < 8) {
        setErrorForLogin(passwordLogin, 'La contraseña debe tener al menos 8 caracteres');
    } else{
        setSuccessForLogin(passwordLogin);
    }
}

function setErrorForLogin(input, message) {
    const formControl = input.parentElement;
    const small = formControl.querySelector('small');

    small.innerText = message;
}

function setSuccessForLogin() {
    // enviar formulario si todos los campos estan bien //
    if (usernameLogin.value !== '' && passwordLogin.value !== '' && passwordLogin.value.length >= 8) {
        formLogin.submit();
    }
}

const smallLogin = document.querySelectorAll('small');

if (formLogin) {
    formLogin.addEventListener('click', () => {
        smallLogin.forEach((item) => {
            item.innerText = '';
        });
    });
}

// menu responsive //
const menuBtn = document.querySelector('.menu-btn');
const menuNav = document.querySelector('.menu__nav');

menuBtn.addEventListener('click', () => {
    menuNav.classList.toggle('menu__nav--active');
});

// menu settings //
const settingsApi = document.querySelector('#api')
const settingsWeb = document.querySelector('#webpage')
const settingsTwilio = document.querySelector('#twilio')

const settings1 = document.querySelector('.settings__api-api')
const settings2 = document.querySelector('.settings__api-web')
const settings4 = document.querySelector('.settings__api-tw')
const settings5 = document.querySelector('.settings__pr')

if (settingsApi) {
    settingsApi.addEventListener('click', () => {
        settings1.classList.add('settings__api-api--active')
        settings2.classList.remove('settings__api-webpage--active')
        settings4.classList.remove('settings__api-twilio--active')
        settings5.classList.remove('settings__pr')
    })
}

if (settingsWeb) {
    settingsWeb.addEventListener('click', () => {
        settings2.classList.add('settings__api-webpage--active')
        settings1.classList.remove('settings__api-api--active')
        settings4.classList.remove('settings__api-twilio--active')
        settings5.classList.remove('settings__pr')
    })
}

if (settingsTwilio) {
    settingsTwilio.addEventListener('click', () => {
        settings4.classList.add('settings__api-twilio--active')
        settings1.classList.remove('settings__api-api--active')
        settings2.classList.remove('settings__api-webpage--active')
        settings5.classList.remove('settings__pr')
    })
}



