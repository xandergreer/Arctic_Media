//
//  LoginView.swift
//  ArcticMedia
//

import SwiftUI

struct LoginView: View {
    @EnvironmentObject var authManager: AuthManager
    @State private var identifier: String = ""
    @State private var password: String = ""
    @State private var isLoading: Bool = false
    @State private var errorMessage: String?
    
    var body: some View {
        NavigationView {
            VStack(spacing: 30) {
                Text("Arctic Media")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                
                Text("Sign in to your media library")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                VStack(spacing: 16) {
                    TextField("Username or Email", text: $identifier)
                        .textFieldStyle(.roundedBorder)
                        .autocapitalization(.none)
                        .autocorrectionDisabled()
                    
                    SecureField("Password", text: $password)
                        .textFieldStyle(.roundedBorder)
                    
                    if let error = errorMessage {
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
                    }
                }
                .padding(.horizontal)
                
                Button(action: handleLogin) {
                    if isLoading {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                    } else {
                        Text("Sign In")
                            .fontWeight(.semibold)
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(isLoading || identifier.isEmpty || password.isEmpty)
                
                Spacer()
            }
            .padding()
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Change Server") {
                        authManager.clearServer()
                    }
                }
            }
        }
    }
    
    private func handleLogin() {
        guard !identifier.isEmpty && !password.isEmpty else { return }
        
        isLoading = true
        errorMessage = nil
        
        Task {
            do {
                let (user, token) = try await APIService.shared.login(identifier: identifier, password: password)
                await MainActor.run {
                    authManager.login(user: user, token: token)
                    isLoading = false
                }
            } catch {
                await MainActor.run {
                    if case APIError.unauthorized = error {
                        errorMessage = "Invalid credentials"
                    } else {
                        errorMessage = "Login failed: \(error.localizedDescription)"
                    }
                    isLoading = false
                }
            }
        }
    }
}

