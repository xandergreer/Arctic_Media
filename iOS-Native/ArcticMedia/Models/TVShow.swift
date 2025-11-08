//
//  TVShow.swift
//  ArcticMedia
//

import Foundation

struct TVShow: Codable, Identifiable {
    let id: String
    let title: String
    let year: Int?
    let poster_url: String?
    let backdrop_url: String?
    let first_air_date: String?
    let seasons: Int?
    let episodes: Int?
    var extra_json: [String: Any]?
    
    enum CodingKeys: String, CodingKey {
        case id, title, year
        case poster_url, backdrop_url
        case first_air_date, seasons, episodes
        case extra_json
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        title = try container.decode(String.self, forKey: .title)
        year = try container.decodeIfPresent(Int.self, forKey: .year)
        poster_url = try container.decodeIfPresent(String.self, forKey: .poster_url)
        backdrop_url = try container.decodeIfPresent(String.self, forKey: .backdrop_url)
        first_air_date = try container.decodeIfPresent(String.self, forKey: .first_air_date)
        seasons = try container.decodeIfPresent(Int.self, forKey: .seasons)
        episodes = try container.decodeIfPresent(Int.self, forKey: .episodes)
        
        if let extraJsonData = try? container.decodeIfPresent([String: AnyCodable].self, forKey: .extra_json) {
            extra_json = extraJsonData.mapValues { $0.value }
        }
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(title, forKey: .title)
        try container.encodeIfPresent(year, forKey: .year)
        try container.encodeIfPresent(poster_url, forKey: .poster_url)
        try container.encodeIfPresent(backdrop_url, forKey: .backdrop_url)
        try container.encodeIfPresent(first_air_date, forKey: .first_air_date)
        try container.encodeIfPresent(seasons, forKey: .seasons)
        try container.encodeIfPresent(episodes, forKey: .episodes)
    }
    
    var posterURL: URL? {
        guard let poster = poster_url ?? extra_json?["poster"] as? String else { return nil }
        if poster.hasPrefix("http") {
            return URL(string: poster)
        }
        return URL(string: "\(AuthManager.shared.serverURL ?? "")\(poster)")
    }
}

struct Season: Codable, Identifiable {
    let id: String
    let title: String
    let season: Int
}

struct Episode: Codable, Identifiable {
    let id: String
    let title: String
    let still: String?
    let air_date: String?
    let episode: Int?
    let first_file_id: String?
    
    var stillURL: URL? {
        guard let still = still else { return nil }
        if still.hasPrefix("http") {
            return URL(string: still)
        }
        return URL(string: "\(AuthManager.shared.serverURL ?? "")\(still)")
    }
}

