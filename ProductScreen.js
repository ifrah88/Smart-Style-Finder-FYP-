import React, { useEffect, useState } from "react";
import {
  View, Text, Image, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator, Alert,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { api, errText } from "../api";
import { theme, SWATCH } from "../theme";

export default function ProductScreen({ route, navigation }) {
  const { pid, score } = route.params || {};
  const [data, setData] = useState(null);

  useEffect(() => {
    api.product(pid, score).then(setData).catch((e) => Alert.alert("Error", errText(e)));
  }, [pid]);

  if (!data) return <View style={s.center}><ActivityIndicator size="large" color={theme.pink} /></View>;
  const p = data.product;

  const ATTRS = [
    ["pricetag-outline", "Product ID", p.product_id],
    ["shirt-outline", "Fabric", p.fabric],
    ["color-palette-outline", "Color", p.colour],
    ["business-outline", "Brand", p.brand],
    ["sparkles-outline", "Style", p.design],
  ];

  return (
    <ScrollView style={{ backgroundColor: theme.bg }} contentContainerStyle={{ paddingBottom: 30 }}>
      <Image source={{ uri: api.imgUrl(p.img_url) }} style={s.hero} />
      <View style={{ padding: 16 }}>
        {p.score != null && (
          <View style={s.badge}><Ionicons name="trophy" size={12} color={theme.pinkDark} /><Text style={s.badgeText}> Match Score: {p.score}%</Text></View>
        )}
        <View style={s.titleRow}>
          <View style={{ flex: 1 }}>
            <Text style={s.title}>{p.title}</Text>
            <Text style={s.brand}>{p.brand}</Text>
          </View>
          <Text style={s.price}>{p.price}</Text>
        </View>

        <View style={s.attrs}>
          {ATTRS.map(([icon, k, v]) => (
            <View key={k} style={s.attrRow}>
              <Ionicons name={icon} size={16} color={theme.pink} />
              <Text style={s.attrKey}>{k}</Text>
              {k === "Color" ? (
                <View style={s.colorVal}>
                  <View style={[s.dot, { backgroundColor: SWATCH[v] || "#ccc" }]} />
                  <Text style={s.attrVal}>{v}</Text>
                </View>
              ) : <Text style={s.attrVal}>{v}</Text>}
            </View>
          ))}
        </View>

        <View style={s.actions}>
          <TouchableOpacity style={s.book} onPress={() => navigation.navigate("Booking", { product: p })}>
            <Ionicons name="calendar-outline" size={18} color="#fff" /><Text style={s.bookText}>  Book Dress</Text>
          </TouchableOpacity>
          <TouchableOpacity style={s.fb} onPress={() => navigation.navigate("Feedback", { product: p })}>
            <Ionicons name="star-outline" size={18} color={theme.pink} /><Text style={s.fbText}>  Give Feedback</Text>
          </TouchableOpacity>
        </View>

        {data.similar?.length > 0 && (
          <>
            <Text style={s.section}>Similar Products</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              {data.similar.map((sp) => (
                <TouchableOpacity key={sp.product_id} style={s.simCard}
                  onPress={() => navigation.push("Product", { pid: sp.product_id })}>
                  <Image source={{ uri: api.imgUrl(sp.img_url) }} style={s.simImg} />
                  <Text style={s.simTitle} numberOfLines={2}>{sp.title}</Text>
                  <Text style={s.simPrice}>{sp.price}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </>
        )}

        {data.reviews?.length > 0 && (
          <>
            <Text style={s.section}>Customer Feedback ({data.reviews.length})</Text>
            {data.reviews.map((r, i) => (
              <View key={i} style={s.review}>
                <View style={s.avatar}><Text style={s.avatarText}>{(r.user_name || "U")[0].toUpperCase()}</Text></View>
                <View style={{ flex: 1 }}>
                  <View style={s.reviewHead}>
                    <Text style={s.reviewName}>{r.user_name}</Text>
                    <Text style={s.stars}>{"★".repeat(r.rating)}{"☆".repeat(5 - r.rating)}</Text>
                  </View>
                  <Text style={s.reviewMsg}>{r.message}</Text>
                </View>
              </View>
            ))}
          </>
        )}
      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  hero: { width: "100%", aspectRatio: 1, backgroundColor: theme.pinkTint, resizeMode: "cover" },
  badge: { flexDirection: "row", alignItems: "center", alignSelf: "flex-start",
    backgroundColor: theme.pinkSoft, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 20, marginBottom: 10 },
  badgeText: { color: theme.pinkDark, fontWeight: "700", fontSize: 12 },
  titleRow: { flexDirection: "row", alignItems: "flex-start" },
  title: { fontSize: 19, fontWeight: "800", color: theme.ink },
  brand: { color: theme.muted, marginTop: 2 },
  price: { color: theme.pinkDark, fontSize: 20, fontWeight: "800", marginLeft: 10 },
  attrs: { marginTop: 14, borderTopWidth: 1, borderTopColor: theme.line },
  attrRow: { flexDirection: "row", alignItems: "center", paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: theme.line },
  attrKey: { color: theme.muted, marginLeft: 10, flex: 1 },
  attrVal: { color: theme.ink, fontWeight: "600", textTransform: "capitalize" },
  colorVal: { flexDirection: "row", alignItems: "center" },
  dot: { width: 12, height: 12, borderRadius: 6, marginRight: 6, borderWidth: 1, borderColor: "rgba(0,0,0,.1)" },
  actions: { gap: 12, marginTop: 18 },
  book: { flexDirection: "row", justifyContent: "center", alignItems: "center", backgroundColor: theme.pink, borderRadius: 12, padding: 15 },
  bookText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  fb: { flexDirection: "row", justifyContent: "center", alignItems: "center", borderWidth: 1.5, borderColor: theme.pink, borderRadius: 12, padding: 15 },
  fbText: { color: theme.pink, fontWeight: "700", fontSize: 15 },
  section: { fontSize: 18, fontWeight: "800", marginTop: 22, marginBottom: 10, color: theme.ink },
  simCard: { width: 120, marginRight: 12 },
  simImg: { width: 120, height: 150, borderRadius: 10, backgroundColor: theme.pinkTint },
  simTitle: { fontSize: 12, marginTop: 5, color: theme.ink },
  simPrice: { fontSize: 12.5, fontWeight: "700", color: theme.pinkDark },
  review: { flexDirection: "row", gap: 10, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: theme.line },
  avatar: { width: 38, height: 38, borderRadius: 19, backgroundColor: theme.pinkSoft, alignItems: "center", justifyContent: "center" },
  avatarText: { color: theme.pinkDark, fontWeight: "700" },
  reviewHead: { flexDirection: "row", justifyContent: "space-between" },
  reviewName: { fontWeight: "700", color: theme.ink },
  stars: { color: theme.star },
  reviewMsg: { color: "#5b5360", marginTop: 2 },
});
