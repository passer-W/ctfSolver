FROM alpine:3.19 AS unzipper
WORKDIR /work
COPY dist.zip /work/
RUN apk add --no-cache unzip && unzip dist.zip -d /work/out && rm dist.zip
RUN if [ -d /work/out/dist ]; then mv /work/out/dist/* /work/out/ && rmdir /work/out/dist; fi

FROM nginx:1.25-alpine
WORKDIR /usr/share/nginx/html
RUN rm -rf /usr/share/nginx/html/*
COPY --from=unzipper /work/out/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80