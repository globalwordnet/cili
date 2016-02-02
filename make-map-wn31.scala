val closeMatches = collection.mutable.Map[String,Seq[String]]()

val replaced = "\\((.*)\\);\\((.*)\\)".r
val leftDeprecate = "\\((.*)\\);(.*)".r
val rightDeprecate = "(.*);\\((.*)\\)".r
val both = "(.*);(.*)".r

val definitionMaps = collection.mutable.Map[String, String]()

for(line <- io.Source.fromFile("../wndb2lmf/defs-wn30-wn31.csv").getLines) {
  val Array(_,wn30,pos,wn31,pos2) = line.split(",")
  if(pos != pos2) {
    System.err.println("pos mismatch")
  } else {
    val wn30key = "%s-%s" format (wn30, pos)
    val wn31key = pos match {
      case "n" =>
        "1%s-n" format wn31
      case "a" =>
        "3%s-a" format wn31
      case "s" =>
        "3%s-s" format wn31
      case "v" =>
        "2%s-v" format wn31
      case "r" =>
        "4%s-r" format wn31
    }
    definitionMaps.put(wn30key, wn31key)
  }
}


val wn30town31 = io.Source.fromFile("/home/jmccrae/projects/wn-rdf/mapping/wn30-31-release.csv").
  getLines.drop(1).map({ line =>
    val Array(wn30, wn31) = line.split(",")
    wn31 match {
      case replaced(x, y) =>
        closeMatches.put(wn30, Seq(x, y))
        wn30 -> "none"
      case leftDeprecate(x, y) =>
        closeMatches.put(wn30, Seq(x))
        wn30 -> y
      case rightDeprecate(x, y) =>
        closeMatches.put(wn30, Seq(y))
        wn30 -> x
      case both(x, y) =>
        closeMatches.put(wn30, Seq(x, y))
        wn30 -> "none"
      case _ =>
        if(wn31 == "none") {
          wn30 -> definitionMaps.getOrElse(wn30, "none")
        } else {
          wn30 -> wn31
        }
    }
  }).toMap

println("@prefix owl:    <http://www.w3.org/2002/07/owl#> .")
println("@prefix pwn31: <http://wordnet-rdf.princeton.edu/wn31/> .")
println("@prefix ili: <http://globalwordnet.org/ili/> .")
println("@prefix skos: <http://www.w3.org/2004/02/skos/core#> .")
println()

val deprecated = new java.io.PrintWriter("changes-in-wn31.csv")
deprecated.println("Status,ILI,WN30,WN31,Synset")

for(line <- io.Source.fromFile("ili-map.ttl").getLines.drop(11)) {
  val elems = line.split("\\s+")
  val wn30key = elems(2).drop(6)
  val iliKey = if(elems(0).startsWith("<")) { "ili:" + elems(0).drop(1).dropRight(1) } else { elems(0) }
  wn30town31.get(wn30key) match {
    case Some("none") =>
      closeMatches.get(wn30key) match {
        case Some(Seq(x, y)) =>
          println(iliKey + " skos:closeMatch pwn31:" + x + " " + elems.drop(3).mkString(" "))
          println(iliKey + " skos:closeMatch pwn31:" + y + " " + elems.drop(3).mkString(" "))
          deprecated.println("deprecated,%s,%s,%s/%s,%s" format (iliKey, wn30key, x, y, elems.drop(5).map(_.replaceAll(",","")).mkString("/")))
       case None =>
          deprecated.println("deprecated,%s,%s,none,%s" format (iliKey, wn30key, elems.drop(5).map(_.replaceAll(",","")).mkString("/")))
      }
    case Some(key) =>
      closeMatches.get(wn30key) match {
        case Some(Seq(x)) =>
          println(iliKey + " skos:closeMatch pwn31:" + x + " " + elems.drop(3).mkString(" "))
        case None =>
      }
      println((iliKey +: elems(1) +: ("pwn31:" + key) +: elems.drop(3)).mkString(" "))
    case None =>
      System.err.println("Lost: " + line)
  }
}

deprecated.flush()
deprecated.close()
