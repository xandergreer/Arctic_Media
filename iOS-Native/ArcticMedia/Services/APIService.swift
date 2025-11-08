//
//  APIService.swift
//  ArcticMedia
//

import Foundation

enum APIError: Error {
    case invalidURL
    case noData
    case decodingError
    case unauthorized
    case serverError(String)
}

class APIService {
    static let shared = APIService()
    
    private init() {}
    
    private func makeRequest<T: Decodable>(
        url: URL,
        method: String = "GET",
        body: Data? = nil
    ) async throws -> T {
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // Add auth token if available
        if let token = AuthManager.shared.authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        if let body = body {
            request.httpBody = body
        }
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.serverError("Invalid response")
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            if httpResponse.statusCode == 401 {
                throw APIError.unauthorized
            }
            throw APIError.serverError("Server error: \(httpResponse.statusCode)")
        }
        
        do {
            let decoder = JSONDecoder()
            return try decoder.decode(T.self, from: data)
        } catch {
            print("Decoding error: \(error)")
            throw APIError.decodingError
        }
    }
    
    // MARK: - Server Validation
    
    func validateServer(url: String) async throws -> Bool {
        guard let serverURL = URL(string: url) else {
            throw APIError.invalidURL
        }
        
        let healthURL = serverURL.appendingPathComponent("health")
        var request = URLRequest(url: healthURL)
        request.timeoutInterval = 10
        
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else {
                return false
            }
            return (200...299).contains(httpResponse.statusCode)
        } catch {
            return false
        }
    }
    
    // MARK: - Authentication
    
    struct LoginRequest: Codable {
        let identifier: String
        let password: String
    }
    
    struct LoginResponse: Codable {
        let user: User
        let token: String
    }
    
    func login(identifier: String, password: String) async throws -> (User, String) {
        guard let serverURL = AuthManager.shared.serverURL,
              let url = URL(string: "\(serverURL)/auth/login") else {
            throw APIError.invalidURL
        }
        
        let loginRequest = LoginRequest(identifier: identifier, password: password)
        let body = try JSONEncoder().encode(loginRequest)
        
        let response: LoginResponse = try await makeRequest(url: url, method: "POST", body: body)
        return (response.user, response.token)
    }
    
    func getCurrentUser() async throws -> User {
        guard let serverURL = AuthManager.shared.serverURL,
              let url = URL(string: "\(serverURL)/auth/me") else {
            throw APIError.invalidURL
        }
        
        return try await makeRequest(url: url)
    }
    
    // MARK: - Movies
    
    struct MoviesResponse: Codable {
        let page: Int
        let page_size: Int
        let total_pages: Int
        let count: Int
        let items: [MediaItem]
    }
    
    func getMovies(page: Int = 1, pageSize: Int = 60, sort: String = "recent") async throws -> MoviesResponse {
        guard let serverURL = AuthManager.shared.serverURL,
              var components = URLComponents(string: "\(serverURL)/api/movies") else {
            throw APIError.invalidURL
        }
        
        components.queryItems = [
            URLQueryItem(name: "page", value: "\(page)"),
            URLQueryItem(name: "page_size", value: "\(pageSize)"),
            URLQueryItem(name: "sort", value: sort)
        ]
        
        guard let url = components.url else {
            throw APIError.invalidURL
        }
        
        return try await makeRequest(url: url)
    }
    
    // MARK: - TV Shows
    
    struct TVShowsResponse: Codable {
        let page: Int
        let page_size: Int
        let total_pages: Int
        let count: Int
        let items: [TVShow]
    }
    
    func getTVShows(page: Int = 1, pageSize: Int = 60, sort: String = "recent") async throws -> TVShowsResponse {
        guard let serverURL = AuthManager.shared.serverURL,
              var components = URLComponents(string: "\(serverURL)/api/tv") else {
            throw APIError.invalidURL
        }
        
        components.queryItems = [
            URLQueryItem(name: "page", value: "\(page)"),
            URLQueryItem(name: "page_size", value: "\(pageSize)"),
            URLQueryItem(name: "sort", value: sort)
        ]
        
        guard let url = components.url else {
            throw APIError.invalidURL
        }
        
        return try await makeRequest(url: url)
    }
    
    // MARK: - Seasons
    
    func getSeasons(showId: String) async throws -> [Season] {
        guard let serverURL = AuthManager.shared.serverURL,
              var components = URLComponents(string: "\(serverURL)/api/tv/seasons") else {
            throw APIError.invalidURL
        }
        
        components.queryItems = [
            URLQueryItem(name: "show_id", value: showId)
        ]
        
        guard let url = components.url else {
            throw APIError.invalidURL
        }
        
        return try await makeRequest(url: url)
    }
    
    // MARK: - Episodes
    
    func getEpisodes(showId: String, season: Int) async throws -> [Episode] {
        guard let serverURL = AuthManager.shared.serverURL,
              var components = URLComponents(string: "\(serverURL)/api/tv/episodes") else {
            throw APIError.invalidURL
        }
        
        components.queryItems = [
            URLQueryItem(name: "show_id", value: showId),
            URLQueryItem(name: "season", value: "\(season)")
        ]
        
        guard let url = components.url else {
            throw APIError.invalidURL
        }
        
        return try await makeRequest(url: url)
    }
    
    // MARK: - Streaming URLs
    
    func getStreamingURL(itemId: String) -> URL? {
        guard let serverURL = AuthManager.shared.serverURL else { return nil }
        return URL(string: "\(serverURL)/stream/\(itemId)/master.m3u8")
    }
    
    func getDirectStreamingURL(itemId: String) -> URL? {
        guard let serverURL = AuthManager.shared.serverURL else { return nil }
        return URL(string: "\(serverURL)/stream/\(itemId)/file")
    }
}

