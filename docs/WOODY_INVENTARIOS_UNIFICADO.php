<?php
// Referencia para reemplazar el MISMO snippet Woody. No ejecutar localmente.
// Si Woody ya proporciona la etiqueta PHP, pegar el contenido sin esta primera línea.
// Reemplazar __INVENTARIOS_MENSUALES_URL__ por la URL HTTPS base, sin /auth/sso.
if (!defined('ABSPATH')) {
    exit;
}

if (!function_exists('calco_inventarios_b64url')) {
    function calco_inventarios_b64url($data)
    {
        return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
    }
}

if (!is_user_logged_in()) {
    echo '';
    return;
}

// Whitelist del servidor: el navegador solo selecciona una clave.
$calco_apps = array(
    'uno_a_uno' => array(
        'audience' => 'inventarios-uno-a-uno',
        'target' => 'https://inventarios-uno-a-uno.calcoweb.net/auth/sso',
        'label' => 'INVENTARIOS UNO A UNO'
    ),
    'mensual' => array(
        'audience' => 'inventarios-mensuales',
        'target' => '__INVENTARIOS_MENSUALES_URL__/auth/sso',
        'label' => 'INVENTARIOS MENSUALES'
    )
);

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['calco_inventarios_sso'])) {
    $nonce = isset($_POST['_wpnonce']) && is_string($_POST['_wpnonce'])
        ? sanitize_text_field(wp_unslash($_POST['_wpnonce'])) : '';
    if (!$nonce || !wp_verify_nonce($nonce, 'calco_inventarios_sso')) {
        wp_die('La solicitud de acceso no es válida.', 'Acceso no autorizado', array('response' => 403));
    }

    // Un formulario antiguo sin selector conserva el destino Uno a Uno.
    $app_key = isset($_POST['calco_inventarios_app'])
        ? wp_unslash($_POST['calco_inventarios_app']) : 'uno_a_uno';
    if (!is_string($app_key) || !array_key_exists($app_key, $calco_apps)) {
        wp_die('Aplicación no permitida.', 'Acceso no autorizado', array('response' => 403));
    }
    $selected_app = $calco_apps[$app_key];
    $target = $selected_app['target'];
    if (strpos($target, '__INVENTARIOS_MENSUALES_URL__') !== false) {
        wp_die('El acceso a Inventarios Mensuales aún no está configurado.',
            'Acceso no disponible', array('response' => 503));
    }

    $user = wp_get_current_user();
    if (!$user || !$user->exists()) {
        wp_die('Usuario no autenticado.', 'Acceso no autorizado', array('response' => 401));
    }

    // Mismo path actual. La clave privada permanece exclusivamente en WordPress.
    $private_key_path = '/etc/calco-intranet/inventarios-uno-a-uno/private.pem';
    if (!is_readable($private_key_path)) {
        wp_die('No fue posible leer la clave de autenticación.', 'Error de configuración', array('response' => 500));
    }
    $private_key_contents = file_get_contents($private_key_path);
    $private_key = openssl_pkey_get_private($private_key_contents);
    if ($private_key === false) {
        wp_die('La clave de autenticación no es válida.', 'Error de configuración', array('response' => 500));
    }

    $now = time();
    $header = array('alg' => 'RS256', 'typ' => 'JWT');
    $payload = array(
        'iss' => 'calco-intranet',
        'aud' => $selected_app['audience'],
        'sub' => $user->user_login,
        'usuario' => $user->user_login,
        'email' => $user->user_email,
        'iat' => $now,
        'nbf' => $now,
        'exp' => $now + 60,
        'jti' => bin2hex(random_bytes(32))
    );
    $encoded_header = calco_inventarios_b64url(wp_json_encode($header));
    $encoded_payload = calco_inventarios_b64url(wp_json_encode($payload));
    $signing_input = $encoded_header . '.' . $encoded_payload;
    $signature = '';
    $signed = openssl_sign($signing_input, $signature, $private_key, OPENSSL_ALGO_SHA256);
    if (!$signed) {
        wp_die('No fue posible generar el inicio de sesión.', 'Error de autenticación', array('response' => 500));
    }
    $jwt = $signing_input . '.' . calco_inventarios_b64url($signature);

    echo '
    <!doctype html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <meta name="referrer" content="no-referrer">
        <title>Ingresando a Inventarios...</title>
    </head>
    <body>
        <form id="calco-inventarios-sso" method="post" action="' . esc_url($target) . '">
            <input type="hidden" name="token" value="' . esc_attr($jwt) . '">
        </form>
        <script>document.getElementById("calco-inventarios-sso").submit();</script>
    </body>
    </html>';
    return;
}

$nonce = wp_create_nonce('calco_inventarios_sso');
$current_url = get_permalink();
foreach ($calco_apps as $app_key => $app_config) {
    echo '
    <div style="text-align:center; padding:30px 0;">
        <form method="post" action="' . esc_url($current_url) . '" target="_blank">
            <input type="hidden" name="calco_inventarios_sso" value="1">
            <input type="hidden" name="calco_inventarios_app" value="' . esc_attr($app_key) . '">
            <input type="hidden" name="_wpnonce" value="' . esc_attr($nonce) . '">
            <button type="submit" style="
                background:#5a3827; color:#ffffff; border:none; padding:14px 28px;
                font-size:18px; font-weight:600; border-radius:5px; cursor:pointer;
            ">' . esc_html($app_config['label']) . '</button>
        </form>
    </div>';
}
