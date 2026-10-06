import Foundation
import Vision
import Darwin

var output: [[String: Any]] = []
if CommandLine.arguments.count < 2 {
    FileHandle.standardError.write(Data("usage: swift ocr_text.swift image.png [image.png ...]\n".utf8))
    exit(1)
}
for path in CommandLine.arguments.dropFirst() {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["zh-Hans", "en-US"]
    request.usesLanguageCorrection = false
    do {
        try VNImageRequestHandler(url: URL(fileURLWithPath: path)).perform([request])
        let lines: [[String: Any]] = (request.results ?? []).compactMap { observation in
            guard let text = observation.topCandidates(1).first else { return nil }
            let box = observation.boundingBox
            return ["text": text.string, "confidence": Double(text.confidence),
                    "normalized_bbox_top_left": [box.minX, 1 - box.maxY, box.maxX, 1 - box.minY]]
        }
        output.append(["path": path, "lines": lines])
    } catch {
        FileHandle.standardError.write(Data("OCR failed for \(path): \(error)\n".utf8))
        exit(1)
    }
}
let data = try JSONSerialization.data(withJSONObject: output, options: [.prettyPrinted, .sortedKeys])
FileHandle.standardOutput.write(data)
FileHandle.standardOutput.write(Data("\n".utf8))
