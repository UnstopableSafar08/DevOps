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
mkdir -p /opt/hello-world
cd /opt/hello-world
gradle init --type java-application --dsl groovy --project-name hello-world --package com.example
```
When prompted:
- Continue? `yes`
- Target Java version: `21`
- Application structure: `1 (Single application project)`
- Test framework: `1 (JUnit 4)`
- Generate build using new APIs: `no`

OUTPUT:
```
[root@linux opt]# cd hello-world
[root@linux hello-world]# ll
total 0
[root@linux hello-world]# 
[root@linux hello-world]# 
[root@linux hello-world]# 
[root@linux hello-world]# mkdir -p /opt/hello-world
cd /opt/hello-world
gradle init --type java-application --dsl groovy --project-name hello-world --package com.example

Enter target Java version (min: 7, default: 21): 21

Select application structure:
  1: Single application project
  2: Application and library project
Enter selection (default: Single application project) [1..2] 1

Select test framework:
  1: JUnit 4
  2: TestNG
  3: Spock
  4: JUnit Jupiter
Enter selection (default: JUnit Jupiter) [1..4] 1

Generate build using new APIs and behavior (some features may change in the next minor release)? (default: no) [yes, no] 


> Task :init
Learn more about Gradle by exploring our Samples at https://docs.gradle.org/9.3.0/samples/sample_building_java_applications.html

BUILD SUCCESSFUL in 23s
1 actionable task: 1 executed
```

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
./gradlew clean build       # Clean and rebuild
./gradlew build -x test     # Build without tests
./gradlew war               # Generate WAR only
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


# Download and Install the Tomcat 11.x
```bash
cd /opt
wget https://archive.apache.org/dist/tomcat/tomcat-11/v11.0.15/bin/apache-tomcat-11.0.15.tar.gz
tar xvzf apache-tomcat-11.0.15.tar.gz 
mv apache-tomcat-11.0.15 tomcat
rm -rf tomcat/webapps/*
rm -rf apache-tomcat-11.0.15.tar.gz 
```

## Copy the war file to the webapps
```bash
cd /opt
cp hello-world/app/build/libs/hello-world.war tomcat/webapps/.

# Stop and Start the Tomcat from binary
./tomcat/bin/shutdown.sh 
./tomcat/bin/startup.sh 

# Check the logs and tomcat port.
tail -f ../tomcat/logs/catalina.out 
ss -lnt
```

## If the firewall is enabled, add firewall rule
```bash
firewall-cmd --permanent -add-port=8080/tcp
firewall-cmd --reload
```

## Check the localhost response.
```bash
curl http://localhost:8080/hello-world/
```

OUTPUT:
```
[root@linux opt]# curl http://localhost:8080/hello-world/
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
[root@linux opt]#
```


# After Deploy on the Tomcat
![Outoput](https://github.com/UnstopableSafar08/DevOps/blob/main/java-app/hello-world.png)



