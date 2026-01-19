# Creating a Java Hello World WAR for Tomcat with Gradle

Quick guide to build a deployable WAR file using Gradle and Java 21.

## Download links:

[Java_Download_link](https://bell-sw.com/pages/downloads/) </br>
[Gradle_Download_link](https://services.gradle.org/distributions/) </br>
[Tomcat_Download_link](https://archive.apache.org/dist/tomcat)


## Prerequisites Installation

### Install Java 21

```bash
cd /opt
sudo wget https://download.bell-sw.com/java/21.0.9+15/bellsoft-jdk21.0.9+15-linux-amd64.tar.gz
sudo tar -xzf bellsoft-jdk21.0.9+15-linux-amd64.tar.gz
sudo rm bellsoft-jdk21.0.9+15-linux-amd64.tar.gz
```

Set environment variables:

```bash
export JAVA_HOME=/opt/jdk-21.0.9
export PATH=$JAVA_HOME/bin:$PATH
```

Add to `.bashrc` or `.bash_profile` for persistence:

```bash
echo 'export JAVA_HOME=/opt/jdk-21.0.9' >> ~/.bashrc
echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

Verify installation:

```bash
java -version
```

### Install Gradle 9.3.0

```bash
cd /opt
sudo wget https://services.gradle.org/distributions/gradle-9.3.0-bin.zip
sudo unzip gradle-9.3.0-bin.zip
sudo rm gradle-9.3.0-bin.zip
```

Set environment variables:

```bash
export GRADLE_HOME=/opt/gradle-9.3.0
export PATH=$GRADLE_HOME/bin:$PATH
```

Add to `.bashrc` or `.bash_profile`:

```bash
echo 'export GRADLE_HOME=/opt/gradle-9.3.0' >> ~/.bashrc
echo 'export PATH=$GRADLE_HOME/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

Verify installation:

```bash
gradle -version
```

## Step 1: Initialize Project

```bash
gradle init --type java-application --dsl groovy --project-name hello-world --package com.example
```
When prompted:
- Continue? `yes`
- Target Java version: `21`
- Application structure: `1 (Single application project)`
- Test framework: `1 (JUnit 4)`
- Generate build using new APIs: `no`

## Step 2: Configure build.gradle

Navigate to `app/build.gradle` and replace with:

```groovy
plugins {
    id 'java'
    id 'war'
}

group = 'com.example'
version = '1.0.0'

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}

repositories {
    mavenCentral()
}

dependencies {
    providedCompile 'jakarta.servlet:jakarta.servlet-api:6.0.0'
    testImplementation 'org.junit.jupiter:junit-jupiter:5.10.0'
    testRuntimeOnly 'org.junit.platform:junit-platform-launcher'
}

war {
    archiveFileName = 'hello-world.war'
}

tasks.named('test') {
    useJUnitPlatform()
}
```

## Step 3: Create Webapp Structure

```bash
mkdir -p app/src/main/webapp/WEB-INF
```

## Step 4: Create web.xml

Create `app/src/main/webapp/WEB-INF/web.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<web-app xmlns="https://jakarta.ee/xml/ns/jakartaee"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="https://jakarta.ee/xml/ns/jakartaee
         https://jakarta.ee/xml/ns/jakartaee/web-app_6_0.xsd"
         version="6.0">
    
    <display-name>Hello World</display-name>
    
    <welcome-file-list>
        <welcome-file>index.html</welcome-file>
    </welcome-file-list>
    
</web-app>
```

## Step 5: Create index.html

Create `app/src/main/webapp/index.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Hello World</title>
</head>
<body>
    <h1>Hello World</h1>
</body>
</html>
```

## Step 6: Delete Unnecessary Files

```bash
rm -rf app/src/main/java/com/example/App.java
rm -rf app/src/test
```

## Step 7: Build WAR

```bash
./gradlew build
```

WAR file location: `app/build/libs/hello-world.war`

## Step 8: Deploy to Tomcat

Copy `hello-world.war` to Tomcat's `webapps` directory and start Tomcat.

Access at: `http://localhost:8080/hello-world/`

## Project Structure

```
hello-world/
├── app/
│   ├── src/main/
│   │   └── webapp/
│   │       ├── WEB-INF/
│   │       │   └── web.xml
│   │       └── index.html
│   └── build.gradle
├── gradlew
└── settings.gradle
```

## Useful Commands

```bash
./gradlew clean build       # Clean and rebuild
./gradlew build -x test     # Build without tests
./gradlew war               # Generate WAR only
```



