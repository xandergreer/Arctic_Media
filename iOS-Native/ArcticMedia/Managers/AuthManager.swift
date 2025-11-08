//
//  AuthManager.swift
//  ArcticMedia
//

import Foundation
import Combine

class AuthManager: ObservableObject {
    static let shared = AuthManager()
    
    @Published var serverURL: String?
    @Published var isAuthenticated: Bool = false
    @Published var currentUser: User?
    @Published var authToken: String?
    
    private let serverURLKey = "arctic_media_server_url"
    private let authTokenKey = "arctic_media_auth_token"
    private let userKey = "arctic_media_user"
    
    private init() {
        loadPersistedData()
    }
    
    private func loadPersistedData() {
        serverURL = UserDefaults.standard.string(forKey: serverURLKey)
        authToken = UserDefaults.standard.string(forKey: authTokenKey)
        
        if let userData = UserDefaults.standard.data(forKey: userKey),
           let user = try? JSONDecoder().decode(User.self, from: userData) {
            currentUser = user
            isAuthenticated = authToken != nil
        }
    }
    
    func setServerURL(_ url: String) {
        self.serverURL = url
        UserDefaults.standard.set(url, forKey: serverURLKey)
    }
    
    func clearServer() {
        serverURL = nil
        UserDefaults.standard.removeObject(forKey: serverURLKey)
        logout()
    }
    
    func login(user: User, token: String) {
        self.currentUser = user
        self.authToken = token
        self.isAuthenticated = true
        
        UserDefaults.standard.set(token, forKey: authTokenKey)
        if let userData = try? JSONEncoder().encode(user) {
            UserDefaults.standard.set(userData, forKey: userKey)
        }
    }
    
    func logout() {
        currentUser = nil
        authToken = nil
        isAuthenticated = false
        
        UserDefaults.standard.removeObject(forKey: authTokenKey)
        UserDefaults.standard.removeObject(forKey: userKey)
    }
}

