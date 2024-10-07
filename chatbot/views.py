import os
from django.shortcuts import render,redirect
from django.http import JsonResponse

from django.contrib import auth
from django.contrib.auth.models import User
from .models import Chat

from django.utils import timezone
from django.contrib.auth.decorators import login_required
from dotenv import load_dotenv
load_dotenv()

# import openai
# Now fetch the API key from the environment variables
# OPENAI_KEY = os.getenv('OPENAI_KEY')
# openai.api_key = OPENAI_KEY 

# def ask_openai(message):
#     response = openai.ChatCompletion.create(
#         model = "gpt-4-0613",
#         # prompt = message,
#         # max_tokens=150,
#         # n=1,
#         # stop=None,
#         # temperature=0.7,
#         messages=[
#             {"role": "system", "content": "You are an helpful assistant."},
#             {"role": "user", "content": message},
#         ]
#     )
#     answer = response.choices[0].message.content.strip()
#     return answer

import google.generativeai as genai
# Load environment variables from .env file
#get api_key from .env file
# Now fetch the API key from the environment variables
API_SECRET_KEY = os.getenv('API_SECRET_KEY')

genai.configure(api_key=API_SECRET_KEY)
def ask_openai(request, message):#gemini
    text = request.POST.get("message")
    model = genai.GenerativeModel("gemini-pro")
    chat = model.start_chat()
    response = chat.send_message(text)
    # ChatBot.objects.create(text_input=text, gemini_output=response.text, user=user)
    # Extract necessary data from response
    return response.text

@login_required
def chatbot(request):
    chats = Chat.objects.filter(user=request.user)

    if request.method == 'POST':
        message = request.POST.get('message')
        response = ask_openai(request, message)

        chat = Chat(user=request.user, message=message, response=response, created_at=timezone.now)
        chat.save()
        return JsonResponse({'message': message, 'response': chat.response_md()})
    return render(request, 'chatbot.html', {'chats': chats})


def login(request):
    if request.method=='POST':
        username = request.POST['username']
        password = request.POST['password']
        user = auth.authenticate(request, username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return redirect('chatbot')
        else:
            error_message = 'Invalid username or password'
            return render(request, 'login.html', {'error_message': error_message})
    else:
        return render(request, 'login.html')

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if password1==password2:
            try:
                user = User.objects.create_user(username, email, password1)
                user.save()
                auth.login(request, user)
                return redirect('chatbot')
            except:
                error_message = 'Error creating account'
            return render(request, 'register.html', {'error_message': error_message})
        else:
            error_message = "Password don't match" 
            return render(request, 'register.html', {'error_message': error_message})
    return render(request, 'register.html')

def logout(request):
    auth.logout(request)
    return redirect('login')