//
//  MediaItem.swift
//  ArcticMedia
//

import Foundation

struct MediaItem: Codable, Identifiable {
    let id: String
    let title: String
    let year: Int?
    let poster_url: String?
    let backdrop_url: String?
    let overview: String?
    let runtime_ms: Int?
    var extra_json: [String: Any]?
    
    enum CodingKeys: String, CodingKey {
        case id, title, year, overview
        case poster_url, backdrop_url, runtime_ms
        case extra_json
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        title = try container.decode(String.self, forKey: .title)
        year = try container.decodeIfPresent(Int.self, forKey: .year)
        poster_url = try container.decodeIfPresent(String.self, forKey: .poster_url)
        backdrop_url = try container.decodeIfPresent(String.self, forKey: .backdrop_url)
        overview = try container.decodeIfPresent(String.self, forKey: .overview)
        runtime_ms = try container.decodeIfPresent(Int.self, forKey: .runtime_ms)
        
        // Decode extra_json as dictionary
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
        try container.encodeIfPresent(overview, forKey: .overview)
        try container.encodeIfPresent(runtime_ms, forKey: .runtime_ms)
    }
    
    var posterURL: URL? {
        guard let poster = poster_url ?? extra_json?["poster"] as? String else { return nil }
        if poster.hasPrefix("http") {
            return URL(string: poster)
        }
        return URL(string: "\(AuthManager.shared.serverURL ?? "")\(poster)")
    }
}

// Helper for decoding Any type
struct AnyCodable: Codable {
    let value: Any
    
    init(_ value: Any) {
        self.value = value
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        
        if let bool = try? container.decode(Bool.self) {
            value = bool
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let string = try? container.decode(String.self) {
            value = string
        } else if let array = try? container.decode([AnyCodable].self) {
            value = array.map { $0.value }
        } else if let dict = try? container.decode([String: AnyCodable].self) {
            value = dict.mapValues { $0.value }
        } else {
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Cannot decode AnyCodable")
        }
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        
        switch value {
        case let bool as Bool:
            try container.encode(bool)
        case let int as Int:
            try container.encode(int)
        case let double as Double:
            try container.encode(double)
        case let string as String:
            try container.encode(string)
        case let array as [Any]:
            try container.encode(array.map { AnyCodable($0) })
        case let dict as [String: Any]:
            try container.encode(dict.mapValues { AnyCodable($0) })
        default:
            throw EncodingError.invalidValue(value, EncodingError.Context(codingPath: container.codingPath, debugDescription: "Cannot encode AnyCodable"))
        }
    }
}

