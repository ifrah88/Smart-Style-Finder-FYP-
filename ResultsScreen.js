import React, { useState, useMemo } from "react";
import { View, Text, Image, FlatList, TouchableOpacity, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { api } from "../api";
import { theme, SWATCH } from "../theme";

const SORTS = [
  { key: "default", label: "Default" },
  { key: "asc",     label: "↑ Low–High" },
  { key: "desc",    label: "↓ High–Low" },
];

function parsePrice(p) {
  return parseInt(String(p || "0").replace(/[^0-9]/g, ""), 10) || 0;
}

export default function ResultsScreen({ route, navigation }) {
  const { type = "Search", results = [], query } = route.params || {};
  const [sort, setSort] = useState("default");

  const sorted = useMemo(() => {
    if (sort === "asc")  return [...results].sort((a, b) => parsePrice(a.price) - parsePrice(b.price));
    if (sort === "desc") return [...results].sort((a, b) => parsePrice(b.price) - parsePrice(a.price));
    return results;
  }, [results, sort]);

  const header = (
    <View>
      <View style={s.banner}>
        <Ionicons name={type === "Image Upload" ? "image" : "search"} size={20} color={theme.pink} />
        <View style={{ flex: 1 }}>
          <Text style={s.bannerTop}>Top {results.length} matching dresses</Text>
          {query ? <Text style={s.bannerQuery}>You searched for: {query}</Text> : null}
          <Text style={s.bannerCount}>{results.length} results found</Text>
        </View>
      </View>
      <View style={s.sortRow}>
        <Text style={s.sortLabel}>Sort by price:</Text>
        {SORTS.map((so) => (
          <TouchableOpacity key={so.key} style={[s.sortBtn, sort === so.key && s.sortBtnOn]}
            onPress={() => setSort(so.key)}>
            <Text style={[s.sortBtnText, sort === so.key && { color: "#fff" }]}>{so.label}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );

  return (
    <FlatList
      style={{ backgroundColor: theme.bg }}
      data={sorted}
      keyExtractor={(it, i) => it.product_id + "_" + i}
      ListHeaderComponent={header}
      contentContainerStyle={{ padding: 14, paddingBottom: 24 }}
      ListEmptyComponent={<Text style={s.empty}>No matches found above the confidence threshold.</Text>}
      renderItem={({ item, index }) => (
        <View style={s.row}>
          <View style={s.numBadge}><Text style={s.numText}>{index + 1}</Text></View>
          <Image source={{ uri: api.imgUrl(item.img_url) }} style={s.thumb} />
          <View style={s.info}>
            <Text style={s.title} numberOfLines={2}>{item.title}</Text>
            <Text style={s.brand}>{item.brand}</Text>
            <View style={s.fabricTag}><Text style={s.fabricText}>{item.fabric || item.design}</Text></View>
            <View style={s.metaRow}>
              <View style={[s.dot, { backgroundColor: SWATCH[item.colour] || "#ccc" }]} />
              <Text style={s.colour}>{item.colour}</Text>
            </View>
            {item.confidence != null && (
              <View style={s.confBadge}>
                <Text style={s.confText}>{item.confidence}% match</Text>
              </View>
            )}
            <View style={s.bottomRow}>
              <Text style={s.price}>{item.price}</Text>
              <TouchableOpacity style={s.viewBtn}
                onPress={() => navigation.navigate("Product", { pid: item.product_id, score: item.confidence })}>
                <Text style={s.viewText}>View Details</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      )}
    />
  );
}

const s = StyleSheet.create({
  banner: { flexDirection: "row", gap: 12, alignItems: "center", backgroundColor: theme.pinkTint,
    borderRadius: 12, padding: 14, marginBottom: 10 },
  bannerTop: { fontWeight: "700", color: theme.ink },
  bannerQuery: { color: theme.pinkDark, fontWeight: "600", fontSize: 13, marginTop: 2 },
  bannerCount: { color: theme.muted, fontSize: 12 },
  sortRow: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: 8,
    marginBottom: 12, paddingHorizontal: 2 },
  sortLabel: { fontSize: 12, color: theme.muted, fontWeight: "500" },
  sortBtn: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20,
    borderWidth: 1.5, borderColor: theme.pink },
  sortBtnOn: { backgroundColor: theme.pink },
  sortBtnText: { fontSize: 12, fontWeight: "600", color: theme.pinkDark },
  row: { flexDirection: "row", backgroundColor: "#fff", borderRadius: 14, borderWidth: 1,
    borderColor: theme.line, padding: 10, marginBottom: 12 },
  numBadge: { position: "absolute", left: 6, top: 6, zIndex: 2, width: 22, height: 22,
    borderRadius: 11, backgroundColor: theme.pink, alignItems: "center", justifyContent: "center" },
  numText: { color: "#fff", fontWeight: "700", fontSize: 12 },
  thumb: { width: 92, height: 120, borderRadius: 10, backgroundColor: theme.pinkTint },
  info: { flex: 1, marginLeft: 12 },
  title: { fontWeight: "600", color: theme.ink, fontSize: 14 },
  brand: { color: theme.muted, fontSize: 12, marginTop: 1 },
  fabricTag: { alignSelf: "flex-start", backgroundColor: theme.pinkSoft, borderRadius: 6,
    paddingHorizontal: 8, paddingVertical: 2, marginTop: 5 },
  fabricText: { color: theme.pinkDark, fontSize: 11, textTransform: "capitalize" },
  metaRow: { flexDirection: "row", alignItems: "center", marginTop: 5 },
  dot: { width: 11, height: 11, borderRadius: 6, marginRight: 6, borderWidth: 1, borderColor: "rgba(0,0,0,.1)" },
  colour: { fontSize: 12.5, color: "#5b5360", textTransform: "capitalize" },
  confBadge: { alignSelf: "flex-start", backgroundColor: theme.pinkSoft, borderRadius: 20,
    paddingHorizontal: 10, paddingVertical: 2, marginTop: 4 },
  confText: { color: theme.pinkDark, fontSize: 11, fontWeight: "700" },
  bottomRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 6 },
  price: { fontWeight: "800", color: theme.pinkDark, fontSize: 15 },
  viewBtn: { borderWidth: 1.5, borderColor: theme.pink, borderRadius: 8, paddingHorizontal: 14, paddingVertical: 7 },
  viewText: { color: theme.pink, fontWeight: "700", fontSize: 12.5 },
  empty: { textAlign: "center", color: theme.muted, padding: 40 },
});
