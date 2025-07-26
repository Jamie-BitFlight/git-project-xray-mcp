// Go test file
package main

import (
    "fmt"
    "net/http"
    "encoding/json"
    db "database/sql"
)

// Struct definition
type User struct {
    ID    int    `json:"id"`
    Name  string `json:"name"`
    Email string `json:"email"`
}

// Interface definition
type Service interface {
    GetUser(id int) (*User, error)
    CreateUser(user User) error
    DeleteUser(id int) error
}

// Type alias
type UserID int

// Constants
const (
    MaxUsers = 100
    DefaultTimeout = 30
)

// Variables
var (
    userCache map[int]*User
    logger    *Logger
)

// Struct with methods
type UserService struct {
    db     *db.DB
    cache  map[int]*User
}

// Method with pointer receiver
func (s *UserService) GetUser(id int) (*User, error) {
    if user, ok := s.cache[id]; ok {
        return user, nil
    }
    
    user := &User{}
    err := s.db.QueryRow("SELECT * FROM users WHERE id = ?", id).Scan(&user.ID, &user.Name, &user.Email)
    if err != nil {
        return nil, err
    }
    
    s.cache[id] = user
    return user, nil
}

// Method with value receiver
func (s UserService) String() string {
    return fmt.Sprintf("UserService with %d cached users", len(s.cache))
}

// Function
func NewUserService(database *db.DB) *UserService {
    return &UserService{
        db:    database,
        cache: make(map[int]*User),
    }
}

// Generic-like function using interface{}
func ProcessData(data interface{}) error {
    switch v := data.(type) {
    case *User:
        return processUser(v)
    case []User:
        return processUsers(v)
    default:
        return fmt.Errorf("unsupported type: %T", v)
    }
}

func processUser(user *User) error {
    // Process single user
    logger.Log("Processing user: " + user.Name)
    return nil
}

func processUsers(users []User) error {
    for _, user := range users {
        if err := processUser(&user); err != nil {
            return err
        }
    }
    return nil
}

// HTTP handler
func userHandler(w http.ResponseWriter, r *http.Request) {
    service := NewUserService(nil)
    user, err := service.GetUser(1)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    
    json.NewEncoder(w).Encode(user)
}

// Logger type
type Logger struct {
    prefix string
}

func (l *Logger) Log(message string) {
    fmt.Printf("%s: %s\n", l.prefix, message)
}

func main() {
    logger = &Logger{prefix: "APP"}
    userCache = make(map[int]*User)
    
    http.HandleFunc("/user", userHandler)
    http.ListenAndServe(":8080", nil)
}