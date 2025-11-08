//
//  ServerConfigView.swift
//  ArcticMedia
//

import SwiftUI

struct ServerConfigView: View {
    @EnvironmentObject var authManager: AuthManager
    @State private var serverURL: String = ""
    @State private var isValidating: Bool = false
    @State private var errorMessage: String?
    
    var body: some View {
        NavigationView {
            VStack(spacing: 30) {
                // Logo
                Image(systemName: "play.circle.fill")
                    .font(.system(size: 80))
                    .foregroundColor(.blue)
                
                Text("Arctic Media")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                
                Text("Connect to your media server")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                VStack(alignment: .leading, spacing: 8) {
                    Text("Server URL")
                        .font(.headline)
                    
                    TextField("e.g., http://192.168.1.100:8000", text: $serverURL)
                        .textFieldStyle(.roundedBorder)
                        .autocapitalization(.none)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                    
                    if let error = errorMessage {
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
                    }
                }
                .padding(.horizontal)
                
                Button(action: validateAndConnect) {
                    if isValidating {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                    } else {
                        Text("Connect")
                            .fontWeight(.semibold)
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(isValidating || serverURL.isEmpty)
                
                Spacer()
            }
            .padding()
            .navigationBarHidden(true)
        }
    }
    
    private func validateAndConnect() {
        guard !serverURL.isEmpty else { return }
        
        isValidating = true
        errorMessage = nil
        
        // Clean up URL
        var cleanURL = serverURL.trimmingCharacters(in: .whitespaces)
        if !cleanURL.hasPrefix("http://") && !cleanURL.hasPrefix("https://") {
            cleanURL = "http://\(cleanURL)"
        }
        
        Task {
            do {
                let isValid = try await APIService.shared.validateServer(url: cleanURL)
                if isValid {
                    await MainActor.run {
                        authManager.setServerURL(cleanURL)
                        isValidating = false
                    }
                } else {
                    await MainActor.run {
                        errorMessage = "Could not connect to server. Please check the URL."
                        isValidating = false
                    }
                }
            } catch {
                await MainActor.run {
                    errorMessage = "Connection failed: \(error.localizedDescription)"
                    isValidating = false
                }
            }
        }
    }
}

