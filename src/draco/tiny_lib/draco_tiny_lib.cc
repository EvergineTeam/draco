#include "draco/draco_features.h"

#ifdef DRACO_TINY_LIB

#include "draco/attributes/geometry_attribute.h"
#include "draco/compression/decode.h"

// If compiling with Visual Studio.
#if defined(_MSC_VER)
	#define EXPORT_API __declspec(dllexport)
#else
	// Other platforms don't need this.
	#define EXPORT_API
#endif  // defined(_MSC_VER)

namespace draco {
extern "C" {

struct DecompressedMesh { void* internalPtr; };
struct Attribute { void* internalPtr; };

struct Data {
	DataType dataType : 32;
	uint32_t dataSize;
	void* data;
};

enum DecompressReturnCode : int {
	DecompressReturnCode_ok = 0,
	DecompressReturnCode_nullParams = -1,
	DecompressReturnCode_cantParseGeomType = -2,
	DecompressReturnCode_cantParseTriangularMesh = -3,
	DecompressReturnCode_invalidGeomType = -3,

	DecompressReturnCode_pointCloudsNotSupportedYet = -1000,
};

int EXPORT_API Draco_Decompress(
	const char* compressedData, size_t compressedDataSize,
	DecompressedMesh* decompressedMesh)
{
	if (compressedData == nullptr || decompressedMesh == nullptr)
		return DecompressReturnCode_nullParams;

	draco::DecoderBuffer buffer;
	buffer.Init(compressedData, compressedDataSize);
	auto statusOr_geomType = draco::Decoder::GetEncodedGeometryType(&buffer);
	if (!statusOr_geomType.ok())
		return DecompressReturnCode_cantParseGeomType;

	draco::Decoder decoder;
	const auto geomType = statusOr_geomType.value();
	if (geomType == TRIANGULAR_MESH) {
		auto statusOr_mesh = decoder.DecodeMeshFromBuffer(&buffer);
		if (!statusOr_mesh.ok())
			return DecompressReturnCode_cantParseTriangularMesh;

		auto mesh = std::move(statusOr_mesh).value();
		auto meshPtr = mesh.release();
		decompressedMesh->internalPtr = (void*)meshPtr;
	}
	else if (geomType == POINT_CLOUD) {
		return DecompressReturnCode_pointCloudsNotSupportedYet;
	}
	else {
		return DecompressReturnCode_invalidGeomType;
	}

	return DecompressReturnCode_ok;
}

static Mesh* InternalMesh(DecompressedMesh m) { return (Mesh*)m.internalPtr; }

void EXPORT_API Draco_DecompressedMesh_Release(DecompressedMesh m) {
	auto mesh = InternalMesh(m);
	delete mesh;
}

uint32_t EXPORT_API Draco_DecompressedMesh_GetNumFaces(DecompressedMesh m) { return InternalMesh(m)->num_faces(); }
uint32_t EXPORT_API Draco_DecompressedMesh_GetNumVertices(DecompressedMesh m) { return InternalMesh(m)->num_points(); }
uint32_t EXPORT_API Draco_DecompressedMesh_GetNumAttributes(DecompressedMesh m) { return InternalMesh(m)->num_attributes(); }

static PointAttribute* InternalAttribute(Attribute a) { return (PointAttribute*)a.internalPtr; }

void EXPORT_API Draco_DecompressedMesh_GetAttribute(DecompressedMesh m, int index, Attribute* attribute)
{
	attribute->internalPtr = nullptr;
	if (attribute == nullptr)
		return;

	const auto mesh = InternalMesh(m);
	const PointAttribute* const attr = mesh->attribute(index);
	if (attr == nullptr)
		return;

	attribute->internalPtr = (void*)attr;
}

void EXPORT_API Draco_DecompressedMesh_GetAttributeByType(DecompressedMesh m, GeometryAttribute::Type attribType, int index, Attribute* attribute)
{
	attribute->internalPtr = nullptr;
	if (attribute == nullptr)
		return;

	const auto mesh = InternalMesh(m);
	const PointAttribute* const attr = mesh->GetNamedAttribute(attribType, index);
	if (attr == nullptr)
		return;

	attribute->internalPtr = (void*)attr;
}

void EXPORT_API Draco_DecompressedMesh_GetAttributeByUniqueId(DecompressedMesh m, uint8_t uniqueId, Attribute* attribute)
{
	attribute->internalPtr = nullptr;
	if (attribute == nullptr)
		return;
	
	const auto mesh = InternalMesh(m);
	const PointAttribute* const attr = mesh->GetAttributeByUniqueId(uniqueId);
	if (attr == nullptr)
		return;
	
	attribute->internalPtr = (void*)attr;
}

void EXPORT_API Draco_DecompressedMesh_GetIndices(DecompressedMesh m, Data* indices)
{
	indices->data = nullptr;
	if (indices == nullptr)
		return;
	
	const auto mesh = InternalMesh(m);
	uint32_t numFaces = mesh->num_faces();

	auto inds = new uint32_t[numFaces * 3];
	for (draco::FaceIndex faceI(0); faceI < numFaces; faceI++) {
		const Mesh::Face& face = mesh->face(faceI);
		auto dst = inds + faceI.value() * 3;
		memcpy(dst, face.data(), sizeof(uint32_t) * 3);
	}
	indices->data = inds;
	indices->dataType = DT_INT32;
	indices->dataSize = numFaces * 3 * sizeof(uint32_t);
}

int32_t EXPORT_API Draco_Attribute_GetAttributeType(Attribute a) { return InternalAttribute(a)->attribute_type(); }
uint32_t EXPORT_API Draco_Attribute_GetDataType(Attribute a) { return InternalAttribute(a)->data_type(); }
uint32_t EXPORT_API Draco_Attribute_GetNumComponents(Attribute a) { return InternalAttribute(a)->num_components(); }
uint32_t EXPORT_API Draco_Attribute_GetUniqueId(Attribute a) { return InternalAttribute(a)->unique_id(); }

void EXPORT_API Draco_Attribute_GetData(DecompressedMesh m, Attribute a, Data* data)
{
	data->data = nullptr;
	if (data == nullptr)
		return;

	const auto mesh = InternalMesh(m);
	auto attrib = InternalAttribute(a);

	const DataType dataType = attrib->data_type();
	const uint32_t numComps = attrib->num_components();
	const uint32_t numVerts = mesh->num_points();
	const uint32_t attribSize = DataTypeLength(dataType) * numComps;
	const size_t dataSize = attribSize * numVerts;
	auto dataPtr = new char[dataSize];
	if (dataPtr == nullptr)
		return;

	data->data = dataPtr;
	data->dataType = dataType;
	data->dataSize = dataSize;

	for (uint32_t i = 0; i < numVerts; i++) {
		attrib->GetMappedValue(PointIndex(i), dataPtr);
		dataPtr += attribSize;
	}
}

void EXPORT_API Draco_Data_Release(Data d) { delete[] (char*)d.data; }

}
}

#endif