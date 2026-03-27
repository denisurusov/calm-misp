package com.example;

import io.javalin.Javalin;

public class HelloWorldApp {
    public static void main(String[] args) {
        var app = Javalin.create().start(7070);
        app.get("/", ctx -> ctx.result("Hello World"));
    }
}
