"""
MIT License

Copyright (c) 2023 Adam Poulemanos

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
"""
TODO: This is currently a non-functional skeleton. Needs to be further developed and set up to handle an array of login and authentication requirements. Very few of the methods/classes are currently integrated, and probably needs refactored.  Work in progress.
"""

import base64
import hashlib
import html
import json
import os
import re
from base64 import b64decode
from typing import Any, Dict, Union
from urllib.parse import parse_qs

import httpx
from attrs import define, field
from urllib3 import util.parse_url


@define
class KeycloakUser:
    """
    Represents a user in the Keycloak authentication system.

    Attributes
    ----------
    username : the username of the user
    password : the password of the user
    access_token : the access token assigned to the user
    pkce_code_verifier : PKCE code verifier for the user
    pkce_code_challenge : PKCE code challenge for the user
    refresh_token : refresh token for the user's session
    """

    username = field()
    password = field()
    ssl_path = field()
    access_token  = field()
    pkce_code_verifier = field()
    pkce_code_challenge = field()
    refresh_token = field()



@define
class KeycloakClient:
    """
    Represents a client in the Keycloak authentication system.

    Attributes
    ----------
    client_id : identifier for the client
    redirect_uri : URI to redirect to after authentication
    auth_code : authentication code for the client
    """

    client_id = field()
    redirect_uri = field()
    auth_code = field()


@define
class KeycloakRealm:
    """
    Represents a realm in the Keycloak authentication system.

    Attributes
    ----------
    code_challenge : PKCE code challenge for the realm
    id_token : ID token for the realm
    """
    provider: str = field()
    realm: str = field()
    ssl_cert_path: str = field()
    config: Dict[str, Any] = field(factory=dict)
    code_challenge = field()
    id_token = field()

    async def discover_settings(self) -> None:
        discovery_url: str = f"{self.provider}/realms/{self.realm}/.well-known/openid-configuration"
        async with httpx.AsyncClient(verify=self.ssl_cert_path) as client:
            response: httpx.Response = await client.get(url=discovery_url)
            if response.status_code == 200:
                self.config = response.json()
            else:
                raise httpx.HTTPStatusError(message=f"Error fetching realm settings: {response.text}", request=response.request)

    async def fetch_auth_methods(self, user_id: str) -> list:
        """
        Fetches available authentication methods for a user.

        :param user_id: The user ID to inspect
        :return: List of authentication methods available
        """
        async with httpx.AsyncClient() as client:
            url = f"{self.provider}/{self.realm}/users/{user_id}/configured-user-storage-credential-types"
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
        return []

class KeycloakAuth:
    """
    A class to handle authentication with a Keycloak server.

    Parameters
    ----------
    provider : URL of the Keycloak provider
    client_id : Client ID for the application
    username : Username for authentication
    password : Password for authentication
    redirect_uri : Redirect URI for the OAuth2 flow

    Attributes
    ----------
    state : State parameter for OAuth2 (initialized as None)
    code_verifier : PKCE code verifier (initialized as None)
    code_challenge : PKCE code challenge (initialized as None)
    auth_code : Authorization code (initialized as None)
    access_token : Access token (initialized as None)
    id_token : ID token (initialized as None)
    refresh_token : Refresh token (initialized as None)

    Methods
    ----------
    generate_pkce_params() : Generates PKCE parameters.
    get_login_page(state="fooobarbaz") : Fetches the login page for authentication.
    authenticate(form_action, cookies) : Authenticates the user using login form data.
    fetch_tokens() : Fetches access and ID tokens using the authorization code.
    decode_jwt(jwt) : Decodes a JWT token and returns the payload.
    direct_authenticate() : Directly authenticates the user using username and password.
    initiate_auth(use_direct_auth=False) : Initiates the authentication flow.
    """

    def __init__(self, provider: str, client_id: str, username: str, password: str, redirect_uri: str):
        """
        Initializes the KeycloakAuth object.

        :param provider: URL of the Keycloak provider
        :param client_id: Client ID for the application
        :param username: Username for authentication
        :param password: Password for authentication
        :param redirect_uri: Redirect URI for the OAuth2 flow
        """
        self.provider = provider
        self.client_id = client_id
        self.username = username
        self.password = password
        self.redirect_uri = redirect_uri
        self.state = None  # State parameter for OAuth2
        self.code_verifier = None  # PKCE code verifier
        self.code_challenge = None  # PKCE code challenge
        self.auth_code = None  # Authorization code
        self.access_token = None  # Access token
        self.id_token = None  # ID token
        self.refresh_token = None

    async def generate_pkce_params(self) -> None:
        """
        Generates PKCE parameters (code_verifier and code_challenge).
        """
        # Generate code_verifier
        code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode('utf-8')
        code_verifier = re.sub('[^a-zA-Z0-9]+', '', code_verifier)
        self.code_verifier = code_verifier

        # Generate code_challenge
        code_challenge = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(code_challenge).decode('utf-8').replace('=', '')
        self.code_challenge = code_challenge

    async def get_login_page(self, state: str = "fooobarbaz") -> Union[Dict[str, Any], None]:
        """
        Fetches the login page and extracts form action and cookies.

        :param state: State parameter for OAuth2 flow
        :return: Dictionary containing form action and cookies or None if failed
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url=f"{self.provider}/protocol/openid-connect/auth",
                params={
                    "response_type": "code",
                    "client_id": self.client_id,
                    "scope": "openid",
                    "redirect_uri": self.redirect_uri,
                    "state": state,
                    "code_challenge": self.code_challenge,
                    "code_challenge_method": "S256",
                },
                allow_redirects=False
            )

            # Check if the request was successful
            if resp.status_code == 200:
                cookie = resp.headers.get('Set-Cookie', '')
                page = resp.text
                if form_action_search := re.search(
                    '<form\\s+.*?\\s+action="(.*?)"', page, re.DOTALL
                ):
                    form_action = html.unescape(form_action_search[1])
                    return {"form_action": form_action, "cookies": cookie}
        return None

    async def authenticate(self, form_action: str, cookies: str) -> str:
        """
        Authenticates the user by posting the login form.

        :param form_action: Action URL of the login form
        :param cookies: Cookies from the login page
        :return: Authorization code
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url=form_action,
                data={"username": self.username, "password": self.password},
                headers={"Cookie": cookies},
                allow_redirects=False
            )

            # Check if authentication was successful, usually a 302 redirect)
            if resp.status_code == 302:
                redirect = resp.headers.get('Location', '')
                query = parse_url(redirect).query
                redirect_params = parse_qs(query)
                if auth_code := redirect_params.get('code', [None])[0]:
                    self.auth_code = auth_code
                    return auth_code
        return ''

    async def fetch_tokens(self) -> Dict[str, Any]:
        """
        Fetches access and ID tokens using the authorization code.

        :return: Dictionary containing access and ID tokens
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url=f"{self.provider}/protocol/openid-connect/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "redirect_uri": self.redirect_uri,
                    "code": self.auth_code,
                    "code_verifier": self.code_verifier,
                },
                allow_redirects=False
            )

            # Check if the request was successful
            if resp.status_code == 200:
                result = resp.json()
                self.access_token = result.get('access_token', '')
                self.id_token = result.get('id_token', '')
                return result
        return {}

    async def decode_jwt(self, jwt: str) -> Dict[str, Any]:
        """
        Decodes a JWT token and returns the payload.

        :param jwt: JWT token string
        :return: Dictionary containing decoded JWT payload
        """
        _, payload, _ = jwt.split('.')
        data = b64decode(payload + '=' * (4 - len(payload) % 4)).decode('utf-8')
        return json.loads(data)

    async def direct_authenticate(self) -> Dict[str, Any]:
        """
        Directly authenticates the user using username and password.

        :return: Dictionary containing access and ID tokens
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url=f"{self.provider}/protocol/openid-connect/token",
                data={
                    "grant_type": "password",
                    "client_id": self.client_id,
                    "username": self.username,
                    "password": self.password,
                },
                allow_redirects=False
            )

            if resp.status_code == 200:
                result = resp.json()
                self.access_token = result.get('access_token', '')
                self.id_token = result.get('id_token', '')
                return result
        return {}

    async def initiate_auth(self, use_direct_auth: bool = False) -> None:
        """
        Initiates the authentication flow.

        :param use_direct_auth: Flag to use direct authentication bypass
        """
        if use_direct_auth:
            await self.direct_authenticate()
        else:
            await self.generate_pkce_params()
            login_page_data = await self.get_login_page()
            if login_page_data:
                auth_code = await self.authenticate(login_page_data['form_action'], login_page_data['cookies'])
                tokens = await self.fetch_tokens()

class KeycloakSessionManager:
    """
    A class to manage sessions with a Keycloak server using the KeycloakAuth class.
    """

    def __init__(self, auth_instance: KeycloakAuth):
        """
        Initializes the KeycloakSessionManager object.

        :param auth_instance: An instance of the KeycloakAuth class.
        """
        self.auth_instance = auth_instance
        self.refresh_interval = 45  # Time in seconds to refresh before the token expires.

    async def refresh_access_token(self):
        """
        Uses the refresh token to obtain a new access token.
        """
        tokens = await self.auth_instance.fetch_tokens()
        # Store the new access token and possibly refresh token.
        self.auth_instance.access_token = tokens.get('access_token', '')
        self.auth_instance.id_token = tokens.get('id_token', '')

    async def ensure_token_validity(self):
        """
        TODO: Implement refresh based on access token.
        Ensures the access token remains valid by periodically refreshing it.
        """
        while True:
            await asyncio.sleep(self.refresh_interval)
            await self.refresh_access_token()


class DeKeyCloaker:
    """
    A class for handling various aspects of authentication cloaking.

    Parameters
    ----------
    auth_details : details necessary for authentication processes

    Attributes
    ----------
    pkce_generator : handles PKCE (Proof Key for Code Exchange) generation
    login_handler : manages login page interactions
    authenticator : handles the authentication process
    token_fetcher : responsible for fetching tokens
    direct_authenticator : manages direct authentication processes

    Methods
    ----------
    initiate_auth(use_direct_auth) : Initiates the authentication process.

    Notes
    -------
    *Private Methods:*
        [Other initializations]
    """
    def __init__(self, auth_details):
        self.pkce_generator = PKCEGenerator()
        self.login_handler = LoginPageHandler(auth_details)
        self.authenticator = Authenticator(auth_details)
        self.token_fetcher = TokenFetcher(auth_details)
        self.direct_authenticator = DirectAuthenticator(auth_details)
        # [Other initializations]

    async def initiate_auth(self, use_direct_auth):


auth_instance = KeycloakAuth(provider="https://keycloak-url",
                             client_id="client-id",
                             username="username",
                             password="password",
                             redirect_uri="http://localhost/callback")
await auth_instance.initiate_auth()

session_manager = KeycloakSessionManager(auth_instance)
# This will keep running in the background, refreshing your token as necessary.
await session_manager.ensure_token_validity()
