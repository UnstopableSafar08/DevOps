package main

import (
    "fmt"
    "os"
    "os/signal"
    "strconv"
    "sync"
    "time"

    MQTT "github.com/eclipse/paho.mqtt.golang"
)

const (
    brokerAddress = "tcp://192.168.121.141:18831" // Update with your EMQX broker address i.e 192.168.121.141
    clientPrefix  = "client-"
    topic         = "test/topic"
    qos           = 2       // 0, 1, 2
    numClients    = 1000    // Number of clients to simulate
)

func main() {
    wg := &sync.WaitGroup{}
    wg.Add(numClients)

    for i := 0; i < numClients; i++ {
        go func(clientID int) {
            defer wg.Done()

            opts := MQTT.NewClientOptions()
            opts.AddBroker(brokerAddress)
            opts.SetClientID(clientPrefix + strconv.Itoa(clientID))

            client := MQTT.NewClient(opts)
            if token := client.Connect(); token.Wait() && token.Error() != nil {
                fmt.Printf("Client %d: Error connecting: %v\n", clientID, token.Error())
                return
            }
            defer client.Disconnect(250)

            for {
                token := client.Publish(topic, byte(qos), false, "Hello from client "+strconv.Itoa(clientID))
                token.Wait()
                if token.Error() != nil {
                    fmt.Printf("Client %d: Error publishing message: %v\n", clientID, token.Error())
                    return
                }
                time.Sleep(1 * time.Second) // Adjust this delay as needed
            }
        }(i)
    }

    // Capture CTRL+C signal to gracefully shutdown
    c := make(chan os.Signal, 1)
    signal.Notify(c, os.Interrupt)
    go func() {
        <-c
        fmt.Println("\nShutting down...")
        wg.Wait()
        os.Exit(0)
    }()

    fmt.Println("Press CTRL+C to exit")
    wg.Wait()
}