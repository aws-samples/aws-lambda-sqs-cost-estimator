FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
COPY *.py ./
EXPOSE 8080
CMD [ "python3", "LambdaDash.py"]

# Commands to build and run docker image
# docker build -t lambda-dash .
# docker run -it -name Lamdba-Cost-Estimator \
#    -m type=bind,source="${pwd}"/input.prop,target=./ \
#    -p 8080:8080 lambda-dash
