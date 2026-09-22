/******/ var __webpack_modules__ = ({

/***/ 4720:
/***/ ((__unused_webpack_module, exports, __webpack_require__) => {

var moduleMap = {
	"./Module": () => {
		return Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_core_angular_core"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_common_angular_common"), __webpack_require__.e("default-webpack_sharing_consume_default_ngx-translate_core_ngx-translate_core"), __webpack_require__.e("default-webpack_sharing_consume_default_x800_shared_data-access_x800_shared_data-access"), __webpack_require__.e("default-webpack_sharing_consume_default_one_angular_one_angular"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_common_http_angular_common_http"), __webpack_require__.e("default-webpack_sharing_consume_default_colsen1991_ngx-translate-extract-marker_colsen1991_ng-e79105"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_router_angular_router"), __webpack_require__.e("default-webpack_sharing_consume_default_ngx-permissions_ngx-permissions"), __webpack_require__.e("default-webpack_sharing_consume_default_x800_software-center_data-access_x800_software-center-a541de"), __webpack_require__.e("default-webpack_sharing_consume_default_x800_software-center_feature-dismissed-updates-button-4d876f"), __webpack_require__.e("common"), __webpack_require__.e("node_modules_pnpm_babel_runtime_7_23_2_node_modules_babel_runtime_helpers_esm_asyncToGenerato-62d3ee5")]).then(() => (() => ((__webpack_require__(9342)))));
	}
};
var get = (module, getScope) => {
	__webpack_require__.R = getScope;
	getScope = (
		__webpack_require__.o(moduleMap, module)
			? moduleMap[module]()
			: Promise.resolve().then(() => {
				throw new Error('Module "' + module + '" does not exist in container.');
			})
	);
	__webpack_require__.R = undefined;
	return getScope;
};
var init = (shareScope, initScope) => {
	if (!__webpack_require__.S) return;
	var name = "default"
	var oldScope = __webpack_require__.S[name];
	if(oldScope && oldScope !== shareScope) throw new Error("Container initialization failed as it has already been initialized with a different share scope");
	__webpack_require__.S[name] = shareScope;
	return __webpack_require__.I(name, initScope);
};

// This exports getters to disallow modifications
__webpack_require__.d(exports, {
	get: () => (get),
	init: () => (init)
});

/***/ })

/******/ });
/************************************************************************/
/******/ // The module cache
/******/ var __webpack_module_cache__ = {};
/******/ 
/******/ // The require function
/******/ function __webpack_require__(moduleId) {
/******/ 	// Check if module is in cache
/******/ 	var cachedModule = __webpack_module_cache__[moduleId];
/******/ 	if (cachedModule !== undefined) {
/******/ 		return cachedModule.exports;
/******/ 	}
/******/ 	// Create a new module (and put it into the cache)
/******/ 	var module = __webpack_module_cache__[moduleId] = {
/******/ 		// no module.id needed
/******/ 		// no module.loaded needed
/******/ 		exports: {}
/******/ 	};
/******/ 
/******/ 	// Execute the module function
/******/ 	__webpack_modules__[moduleId](module, module.exports, __webpack_require__);
/******/ 
/******/ 	// Return the exports of the module
/******/ 	return module.exports;
/******/ }
/******/ 
/******/ // expose the modules object (__webpack_modules__)
/******/ __webpack_require__.m = __webpack_modules__;
/******/ 
/******/ // expose the module cache
/******/ __webpack_require__.c = __webpack_module_cache__;
/******/ 
/************************************************************************/
/******/ /* webpack/runtime/create fake namespace object */
/******/ (() => {
/******/ 	var getProto = Object.getPrototypeOf ? (obj) => (Object.getPrototypeOf(obj)) : (obj) => (obj.__proto__);
/******/ 	var leafPrototypes;
/******/ 	// create a fake namespace object
/******/ 	// mode & 1: value is a module id, require it
/******/ 	// mode & 2: merge all properties of value into the ns
/******/ 	// mode & 4: return value when already ns object
/******/ 	// mode & 16: return value when it's Promise-like
/******/ 	// mode & 8|1: behave like require
/******/ 	__webpack_require__.t = function(value, mode) {
/******/ 		if(mode & 1) value = this(value);
/******/ 		if(mode & 8) return value;
/******/ 		if(typeof value === 'object' && value) {
/******/ 			if((mode & 4) && value.__esModule) return value;
/******/ 			if((mode & 16) && typeof value.then === 'function') return value;
/******/ 		}
/******/ 		var ns = Object.create(null);
/******/ 		__webpack_require__.r(ns);
/******/ 		var def = {};
/******/ 		leafPrototypes = leafPrototypes || [null, getProto({}), getProto([]), getProto(getProto)];
/******/ 		for(var current = mode & 2 && value; typeof current == 'object' && !~leafPrototypes.indexOf(current); current = getProto(current)) {
/******/ 			Object.getOwnPropertyNames(current).forEach((key) => (def[key] = () => (value[key])));
/******/ 		}
/******/ 		def['default'] = () => (value);
/******/ 		__webpack_require__.d(ns, def);
/******/ 		return ns;
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/define property getters */
/******/ (() => {
/******/ 	// define getter functions for harmony exports
/******/ 	__webpack_require__.d = (exports, definition) => {
/******/ 		for(var key in definition) {
/******/ 			if(__webpack_require__.o(definition, key) && !__webpack_require__.o(exports, key)) {
/******/ 				Object.defineProperty(exports, key, { enumerable: true, get: definition[key] });
/******/ 			}
/******/ 		}
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/ensure chunk */
/******/ (() => {
/******/ 	__webpack_require__.f = {};
/******/ 	// This file contains only the entry chunk.
/******/ 	// The chunk loading function for additional chunks
/******/ 	__webpack_require__.e = (chunkId) => {
/******/ 		return Promise.all(Object.keys(__webpack_require__.f).reduce((promises, key) => {
/******/ 			__webpack_require__.f[key](chunkId, promises);
/******/ 			return promises;
/******/ 		}, []));
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/get javascript chunk filename */
/******/ (() => {
/******/ 	// This function allow to reference async chunks
/******/ 	__webpack_require__.u = (chunkId) => {
/******/ 		// return url for filenames based on template
/******/ 		return "" + chunkId + "." + {"default-webpack_sharing_consume_default_rxjs_rxjs":"4a7faa2fe4170dab","default-webpack_sharing_consume_default_angular_core_angular_core":"2e79927b83eb1bc4","default-webpack_sharing_consume_default_angular_common_angular_common":"12d0f52d5c59a71b","default-webpack_sharing_consume_default_ngx-translate_core_ngx-translate_core":"ad822ccef5b9894d","default-webpack_sharing_consume_default_x800_shared_data-access_x800_shared_data-access":"69d10037545d9b15","default-webpack_sharing_consume_default_one_angular_one_angular":"cb97ce9cd622fbca","default-webpack_sharing_consume_default_angular_common_http_angular_common_http":"6d38419eb59802a0","default-webpack_sharing_consume_default_colsen1991_ngx-translate-extract-marker_colsen1991_ng-e79105":"2fbbb03c1c4498a2","default-webpack_sharing_consume_default_angular_router_angular_router":"ad6a8ed1c20cad0c","default-webpack_sharing_consume_default_ngx-permissions_ngx-permissions":"2bd3e6bcbdea9e89","default-webpack_sharing_consume_default_x800_software-center_data-access_x800_software-center-a541de":"cd6c5f8fa1c6f53f","default-webpack_sharing_consume_default_x800_software-center_feature-dismissed-updates-button-4d876f":"1d4f48ade4d318b2","common":"347177d23a57f6af","node_modules_pnpm_babel_runtime_7_23_2_node_modules_babel_runtime_helpers_esm_asyncToGenerato-62d3ee5":"3a484086e1fd8689","default-webpack_sharing_consume_default_rxjs_operators_rxjs_operators":"0077e19891258fe0","default-node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_-38e043":"4d759a753a5e956a","default-node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_-3dabbf":"c446ff2a0ef3303b","node_modules_pnpm_angular_core_17_0_7_rxjs_7_8_1_zone_js_0_14_2_node_modules_angular_core_fes-a90fed":"4bcffcdd326c55e4","node_modules_pnpm_angular_core_17_0_7_rxjs_7_8_1_zone_js_0_14_2_node_modules_angular_core_fes-9610d2":"f64d68401d319ea9","default-node_modules_pnpm_angular_platform-browser_17_0_7__angular_animations_17_0_7__angular-0f3a0c":"7dfbb0f130cf659f","default-webpack_sharing_consume_default_angular_platform-browser_angular_platform-browser":"30fc0c79d33efb53","default-node_modules_pnpm_angular_router_17_0_7__angular_common_17_0_7__angular_core_17_0_7__-f2ac5b":"7e7d72da3994333f","node_modules_pnpm_colsen1991_ngx-translate-extract-marker_2_0_8__angular_common_17_0_7__angul-1cc127":"f9793c97c7a87f87","default-node_modules_pnpm_microsoft_signalr_8_0_0_node_modules_microsoft_signalr_dist_esm_index_js":"2fa770c854bcdf3a","node_modules_pnpm_babel_runtime_7_23_2_node_modules_babel_runtime_helpers_esm_asyncToGenerato-62d3ee1":"4545f5ebdf012e44","default-node_modules_pnpm_ngx-translate_core_14_0_0__angular_core_17_0_7_rxjs_7_8_1_node_modu-6e2a23":"0a683621be6c0645","default-node_modules_pnpm_one_angular_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_r-38e6b8":"0f1c262687c6f4d5","default-webpack_sharing_consume_default_angular_core_rxjs-interop_angular_core_rxjs-interop":"fcd697e9e0a68494","default-libs_shared_data-access_src_index_ts":"5e3cac5d2af55c4b","default-webpack_sharing_consume_default_date-fns_date-fns":"1ef07f8815999288","default-libs_shared_ui_components_src_index_ts":"426aacc6f35f556d","node_modules_pnpm_babel_runtime_7_23_2_node_modules_babel_runtime_helpers_esm_asyncToGenerato-62d3ee2":"6d7a543693188dfe","default-webpack_sharing_consume_default_x800_shared_ui_components_x800_shared_ui_components":"4446e3a3ff22868a","node_modules_pnpm_babel_runtime_7_23_2_node_modules_babel_runtime_helpers_esm_asyncToGenerato-62d3ee3":"88a13995e01ddbf5","default-libs_software-center_ui_src_index_ts":"659cb185b7f01493","node_modules_pnpm_date-fns_2_29_3_node_modules_date-fns_esm_index_js":"f9839c6f756bc95a","default-node_modules_pnpm_ngx-permissions_16_0_1__angular_core_17_0_7__angular_router_17_0_7_-dba0f7":"52623e0306593588","default-node_modules_pnpm_rxjs_7_8_1_node_modules_rxjs_dist_esm_internal_operators_auditTime_-a4e86f":"2ff40116a2f0e23f","node_modules_pnpm_rxjs_7_8_1_node_modules_rxjs_dist_esm_operators_index_js":"81584f2a641070ef","node_modules_pnpm_rxjs_7_8_1_node_modules_rxjs_dist_esm_index_js":"e3064cc751de51b5","node_modules_pnpm_babel_runtime_7_23_2_node_modules_babel_runtime_helpers_esm_asyncToGenerato-62d3ee4":"24391636c69ba208","polyfills-dom":"cf1393845cc94017","polyfills-core-js":"f3df50b10209e0bd","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-d2d70a":"89a18d60863387ed","default-node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0-e8bf60":"3a7c12b49118886e","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-bb42be":"76c6271803496058","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-3ca660":"7d081771bce3da8e","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-042f48":"ded7b83f278484aa","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-02ac18":"a0bf39ecd0232a7b","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-2a5c1e":"b67d876487d39bc7","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-8a67f0":"60c8f08e1f2c3fc1","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-bd27df":"ecda4e3e9b53a3be","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-16103f":"73d50de7265087bb","default-node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0-a872bb":"e969b8f28b585599","default-node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0-664783":"25d63f59582e3828","default-node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0-4d995b":"e2f84ec732e66d07","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-f97492":"844601ee7714677e","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-70697f":"a629852ead3d9046","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-61a3ef":"895e7c8724395a73","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-d1f1fd":"8b066a441ce6ac72","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-677fa2":"a686a484bdadb9a5","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-aa6784":"0065edce531cb7a4","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-1c0cce":"53a19c2f306aa080","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-b2ad66":"d01e74626c57c3fa","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-7249a0":"01c70737f553480b","default-node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0-cd5e51":"45016746cd5153f8","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-e94e43":"fe94fb15d0587d37","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-4aa515":"1f467ef67631aa12","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-324b64":"eca57d531a27ed98","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-996788":"f79c6b0dabb57fbc","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-04599d":"2c973dadb1a4a3eb","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-5ca6ec":"6e4c2e36aaa91cba","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-76eb03":"53e015ffddd64f9d","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-82304a":"25e4a842df7302da","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-5917bb":"1964fc212a6a51a5","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-3f7cc2":"696498a6de8e48f5","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-32c43f":"85b1af5de8a33a98","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-8e83b7":"e4148a833ebcc0a0","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-edf16c":"17305d2fa5c333da","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-0e25bc":"627efbbff776433e","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-9efea1":"41c527eed32e57e3","default-node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0-581556":"c29e6f5010fcddb4","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-b1ddac":"f6111e423ddfe3fa","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-4997ef":"90888971aefb948d","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-1a0203":"0611149f544fe784","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-1a8549":"ed6b8c3fe8e05c17","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-8e2491":"4d016c59f8be63dc","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-f07bbd":"6beb28932a3dec50","default-node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0-0db3bd":"a41594c354a96720","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-d57dab":"294c6ff6a8701c95","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-75348b":"834e8dd0c2d3fabc","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-4542c3":"3bd6e67f8e2eae3c","default-node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0-940c0b":"108c394ae6544f25","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-dd6bc3":"18dbf88d612dcb76","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-641314":"4bb6bb95e52287d9","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-43999c":"2452b9bb1b3efcfb","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-2c6d5f":"c87e81f92f9bbf47","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-196b93":"8ca28991a9bf9058","default-node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0-41704e":"35796d1483ca86cd","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-0e3505":"e55e957f07be7be8","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-c93115":"f44f8d3c09d5ad57","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-e4484e":"4306dec1561c9acf","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-2b7cf2":"11b9bae6bfdcb6a7","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-c1b4c4":"060909fd3d041614","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-5fdb24":"35859b825ae773e7","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-f91b8b":"93cc76687e15580c","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-1f32cf":"1bcc6607b05ce50a","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-725356":"679059614047acc4","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-bbd488":"e31624d524c61cab","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-d32075":"91cd3ad80f71c827","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-2f6c31":"03de9bcfe74d1d7b","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-40579a":"bb222e84d26a651a","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-e6191a":"6982f61a028f5414","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-e3c478":"96c313ea69f00755","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-1dd63b":"cb18487868f00d18","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-0b0391":"28dd4d8f8b20cbc9","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-27f491":"d984b560443cabb7","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-84de0d":"d2fbf3be451e83e1","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-21385b":"378f20932b36c8c2","node_modules_pnpm_one_web-components_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_ro-1ba35d":"8921cd9672491495","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-cab2e8":"527a6e4e14c8f8e9","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-24e935":"98bae55384aba503","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-6c842b":"7cdfb637b27f0ae1","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-cdd8d1":"08cac62859f91848","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-3d7ec9":"bce52bd0fd3abbeb","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-6811af":"e4abb7cffbeb7c5a","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-6c399b":"26436ac83acd9639","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-087d69":"48dbce712a3a7d26","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-47a772":"236fa88681d9df89","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-5c01b3":"c95ea816a336ef77","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-b3a7aa":"a9c832cd4f354a83","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-d3180d":"b22f01c0f2ccb2d6","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-6bcc3a":"436db0a9ab54995f","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-86d04d":"ea8b9c4f7d5a4178","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-5a24bd":"098ae112d4c3b59d","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-027fb8":"8fe61a38775d7b32","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-f92c2e":"ebb05e781a52beb8","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-ee1c09":"af9b16852f77c33e","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-471cd4":"07c3997326da74d4","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-c7c61a":"8c93c52ae0ab35b9","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-a5ba77":"133d3f70ac674cfc","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-6c9708":"25ca0aa5e53e45a8","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-3a778b":"ec87e26c009c6034","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-54b977":"baa8f54068d989c5","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-bad041":"7f45d38eeec69307","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-682c14":"73ac02beb8842e34","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-273634":"4ca91477cb2df63c","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-5a5927":"df9e3c3ba45bf505","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-4d97a1":"883ac6bb69f4f6a3","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-1e6f8c":"c2f9e39a3368d22b","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-031f11":"d2d44e6f344b574a","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-33a355":"2bde206626f58e65","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-e001b7":"7aa89127b3dde62a","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-6b83d0":"ae273cc71050ccf0","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-de6018":"a008d8dd8cbdd4e5","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-36bb03":"adb1f6d78749602b","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-63f521":"c2487ff32b0c3161","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-47eacc":"e39d2757dac43bf0","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-830577":"407f28a05c8d71da","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-303c1e":"0ed346898f2bbdcd","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-8283d3":"94382171860c5614","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-51c225":"69d75627f01adfea","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-830c56":"14709bb176a72a3d","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-f08287":"5d832e12b0af6706","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-b4e7be":"be25cff6bc65b0ee","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-c6c279":"38931739bb8e49c8","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-a2d4a8":"46685d186370e61d","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-6507ca":"40d7c49f02a9ce66","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-72790f":"2c722a2acda3ad6e","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-be40dd":"370ab812fef13b49","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-f6c7ef":"f1369bebc2f560b8","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-da7aba":"b04bcf18fdd64a0b","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-2e2939":"66e7a559f42b61e0","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-119769":"9835870982a1c4ba","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-cdcc32":"bebefb5804f1521c","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-7c5cbb":"3804a79918d93f1c","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-f016cd":"4bdc2093c5f06835","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-23d0a1":"864d52e543e8c00f","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-43cb1b":"42a6b906130d5c4c","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-827729":"bbfc3f926814ff66","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-401ceb":"f85b29c6cb485457","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-a3335f":"2bbb422b33d13309","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-3c5c2f":"9a6e810ceb2e2f5b","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-52ce61":"2aa8e97d512d9455","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-2ad6fc":"bb4e7d4b413251ee","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-a18db2":"1afc922134a877b5","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-e258a8":"b0bce04f8744111a","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-099e2c":"abef2572dd6bcdce","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-f95caa":"6c1e94ffd34c45b2","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-6d4785":"5b183895bfe551c0","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-9d72fd":"2d5d49457ca083fa","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-5ffcc6":"eaab1b76e8708b66","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-ce488e":"c67d7860b0f3c3a4","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-5bd528":"fd17319b7b1eafa8","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-b5c390":"0e117ee5db2ba118","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-333b19":"6b0ac2b80262eb6b","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-4c5838":"8bdad44c971a2894","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-576e6a":"d84203398ee747d8","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-3386d0":"a03dfc712d724b4a","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-780be9":"caa103c4e9bfe305","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-b319eb":"ca5d4ec680aabfe2","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-17484d":"923789df685eab08","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-635ed4":"3b89d68f8b99f52a","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-be7640":"0c68016e3c9a83a4","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-1e922a":"a286ec7958d068d9","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-2461a5":"9fdff2dee91667b0","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-81a0ad":"a7a4f2cfcc2c0fd5","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-520d1d":"27abf98b5f024fae","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-8f07f2":"00514cabcd229818","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-24d8cc":"9c8c0636d1183bf4","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-85c01e":"2610afc7ae3647fd","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-dc9276":"adfe7cea3e3655c1","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-eb7761":"737bb60f241c4ea1","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-6505ca":"5005f220c89cbb3c","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-c4357b":"19db7a49c303b249","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-13caa9":"ab1f3356ecb0a0bd","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-0b7ff5":"4439ec4a94bf66bb","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-5cf556":"734f30331a3585c1","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-2f0dea":"151c12065a953199","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-1a7799":"626e377316f57133","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-55ff82":"061e6bc678dc5f5f","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-e9a0d2":"f8e9a648b6c809d2","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-290cf8":"b91c0e45b0c1410d","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-7c25d3":"9afa7696907961b3","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-d97473":"8419c693b4351129","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-77ea7b":"200496880ecf2753","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-69f4a0":"addd2dda08f03f7e","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-eba76f":"72a73778c7d3f72e","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-d251f9":"ddf6c71b755f54db","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-37aa44":"3c783fa0884bdc3a","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-29336c":"cdf026ee6222c7c2","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-80660d":"9c262a34d0f1f61a","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-824d9f":"ae67ff8088d23163","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-2582d6":"815d1f903e94f11a","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-08f34f":"56e551a5830c1e96","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-bb55d1":"d11e43f6dbfd406c","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-da6014":"ca48fdd62435d773","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-c1c732":"8de9bac2eccf49cb","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-b06a13":"868f157263b7f31d","node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_angular_-3e0685":"76bae26d0d857429"}[chunkId] + ".js";
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/get mini-css chunk filename */
/******/ (() => {
/******/ 	// This function allow to reference async chunks
/******/ 	__webpack_require__.miniCssF = (chunkId) => {
/******/ 		// return url for filenames based on template
/******/ 		return undefined;
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/hasOwnProperty shorthand */
/******/ (() => {
/******/ 	__webpack_require__.o = (obj, prop) => (Object.prototype.hasOwnProperty.call(obj, prop))
/******/ })();
/******/ 
/******/ /* webpack/runtime/load script */
/******/ (() => {
/******/ 	var inProgress = {};
/******/ 	var dataWebpackPrefix = "software-center:";
/******/ 	// loadScript function to load a script via script tag
/******/ 	__webpack_require__.l = (url, done, key, chunkId) => {
/******/ 		if(inProgress[url]) { inProgress[url].push(done); return; }
/******/ 		var script, needAttach;
/******/ 		if(key !== undefined) {
/******/ 			var scripts = document.getElementsByTagName("script");
/******/ 			for(var i = 0; i < scripts.length; i++) {
/******/ 				var s = scripts[i];
/******/ 				if(s.getAttribute("src") == url || s.getAttribute("data-webpack") == dataWebpackPrefix + key) { script = s; break; }
/******/ 			}
/******/ 		}
/******/ 		if(!script) {
/******/ 			needAttach = true;
/******/ 			script = document.createElement('script');
/******/ 			script.type = "module";
/******/ 			script.charset = 'utf-8';
/******/ 			script.timeout = 120;
/******/ 			if (__webpack_require__.nc) {
/******/ 				script.setAttribute("nonce", __webpack_require__.nc);
/******/ 			}
/******/ 			script.setAttribute("data-webpack", dataWebpackPrefix + key);
/******/ 	
/******/ 			script.src = __webpack_require__.tu(url);
/******/ 		}
/******/ 		inProgress[url] = [done];
/******/ 		var onScriptComplete = (prev, event) => {
/******/ 			// avoid mem leaks in IE.
/******/ 			script.onerror = script.onload = null;
/******/ 			clearTimeout(timeout);
/******/ 			var doneFns = inProgress[url];
/******/ 			delete inProgress[url];
/******/ 			script.parentNode && script.parentNode.removeChild(script);
/******/ 			doneFns && doneFns.forEach((fn) => (fn(event)));
/******/ 			if(prev) return prev(event);
/******/ 		}
/******/ 		var timeout = setTimeout(onScriptComplete.bind(null, undefined, { type: 'timeout', target: script }), 120000);
/******/ 		script.onerror = onScriptComplete.bind(null, script.onerror);
/******/ 		script.onload = onScriptComplete.bind(null, script.onload);
/******/ 		needAttach && document.head.appendChild(script);
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/make namespace object */
/******/ (() => {
/******/ 	// define __esModule on exports
/******/ 	__webpack_require__.r = (exports) => {
/******/ 		if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 			Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 		}
/******/ 		Object.defineProperty(exports, '__esModule', { value: true });
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/sharing */
/******/ (() => {
/******/ 	__webpack_require__.S = {};
/******/ 	var initPromises = {};
/******/ 	var initTokens = {};
/******/ 	__webpack_require__.I = (name, initScope) => {
/******/ 		if(!initScope) initScope = [];
/******/ 		// handling circular init calls
/******/ 		var initToken = initTokens[name];
/******/ 		if(!initToken) initToken = initTokens[name] = {};
/******/ 		if(initScope.indexOf(initToken) >= 0) return;
/******/ 		initScope.push(initToken);
/******/ 		// only runs once
/******/ 		if(initPromises[name]) return initPromises[name];
/******/ 		// creates a new share scope if needed
/******/ 		if(!__webpack_require__.o(__webpack_require__.S, name)) __webpack_require__.S[name] = {};
/******/ 		// runs all init snippets from all modules reachable
/******/ 		var scope = __webpack_require__.S[name];
/******/ 		var warn = (msg) => {
/******/ 			if (typeof console !== "undefined" && console.warn) console.warn(msg);
/******/ 		};
/******/ 		var uniqueName = "software-center";
/******/ 		var register = (name, version, factory, eager) => {
/******/ 			var versions = scope[name] = scope[name] || {};
/******/ 			var activeVersion = versions[version];
/******/ 			if(!activeVersion || (!activeVersion.loaded && (!eager != !activeVersion.eager ? eager : uniqueName > activeVersion.from))) versions[version] = { get: factory, from: uniqueName, eager: !!eager };
/******/ 		};
/******/ 		var initExternal = (id) => {
/******/ 			var handleError = (err) => (warn("Initialization of sharing external failed: " + err));
/******/ 			try {
/******/ 				var module = __webpack_require__(id);
/******/ 				if(!module) return;
/******/ 				var initFn = (module) => (module && module.init && module.init(__webpack_require__.S[name], initScope))
/******/ 				if(module.then) return promises.push(module.then(initFn, handleError));
/******/ 				var initResult = initFn(module);
/******/ 				if(initResult && initResult.then) return promises.push(initResult['catch'](handleError));
/******/ 			} catch(err) { handleError(err); }
/******/ 		}
/******/ 		var promises = [];
/******/ 		switch(name) {
/******/ 			case "default": {
/******/ 				register("@angular/common/http", "17.0.7", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_core_angular_core"), __webpack_require__.e("default-webpack_sharing_consume_default_rxjs_operators_rxjs_operators"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_common_angular_common"), __webpack_require__.e("default-node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_-38e043")]).then(() => (() => (__webpack_require__(9841))))));
/******/ 				register("@angular/common", "17.0.7", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_angular_core_angular_core"), __webpack_require__.e("default-node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_-3dabbf")]).then(() => (() => (__webpack_require__(3891))))));
/******/ 				register("@angular/core/primitives/signals", "17.0.7", () => (__webpack_require__.e("node_modules_pnpm_angular_core_17_0_7_rxjs_7_8_1_zone_js_0_14_2_node_modules_angular_core_fes-a90fed").then(() => (() => (__webpack_require__(125))))));
/******/ 				register("@angular/core/rxjs-interop", "17.0.7", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_core_angular_core"), __webpack_require__.e("default-webpack_sharing_consume_default_rxjs_operators_rxjs_operators"), __webpack_require__.e("common")]).then(() => (() => (__webpack_require__(5314))))));
/******/ 				register("@angular/core", "17.0.7", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_rxjs_operators_rxjs_operators"), __webpack_require__.e("node_modules_pnpm_angular_core_17_0_7_rxjs_7_8_1_zone_js_0_14_2_node_modules_angular_core_fes-9610d2")]).then(() => (() => (__webpack_require__(6629))))));
/******/ 				register("@angular/platform-browser", "17.0.7", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_angular_core_angular_core"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_common_angular_common"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_common_http_angular_common_http"), __webpack_require__.e("default-node_modules_pnpm_angular_platform-browser_17_0_7__angular_animations_17_0_7__angular-0f3a0c")]).then(() => (() => (__webpack_require__(6788))))));
/******/ 				register("@angular/router", "17.0.7", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_core_angular_core"), __webpack_require__.e("default-webpack_sharing_consume_default_rxjs_operators_rxjs_operators"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_common_angular_common"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_platform-browser_angular_platform-browser"), __webpack_require__.e("default-node_modules_pnpm_angular_router_17_0_7__angular_common_17_0_7__angular_core_17_0_7__-f2ac5b")]).then(() => (() => (__webpack_require__(3293))))));
/******/ 				register("@colsen1991/ngx-translate-extract-marker", "2.0.8", () => (__webpack_require__.e("node_modules_pnpm_colsen1991_ngx-translate-extract-marker_2_0_8__angular_common_17_0_7__angul-1cc127").then(() => (() => (__webpack_require__(6030))))));
/******/ 				register("@microsoft/signalr", "8.0.0", () => (Promise.all([__webpack_require__.e("default-node_modules_pnpm_microsoft_signalr_8_0_0_node_modules_microsoft_signalr_dist_esm_index_js"), __webpack_require__.e("node_modules_pnpm_babel_runtime_7_23_2_node_modules_babel_runtime_helpers_esm_asyncToGenerato-62d3ee1")]).then(() => (() => (__webpack_require__(1784))))));
/******/ 				register("@ngx-translate/core", "14.0.0", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_core_angular_core"), __webpack_require__.e("default-webpack_sharing_consume_default_rxjs_operators_rxjs_operators"), __webpack_require__.e("default-node_modules_pnpm_ngx-translate_core_14_0_0__angular_core_17_0_7_rxjs_7_8_1_node_modu-6e2a23")]).then(() => (() => (__webpack_require__(8285))))));
/******/ 				register("@one/angular", "6.10.0", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_core_angular_core"), __webpack_require__.e("default-webpack_sharing_consume_default_rxjs_operators_rxjs_operators"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_common_angular_common"), __webpack_require__.e("default-node_modules_pnpm_one_angular_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_r-38e6b8")]).then(() => (() => (__webpack_require__(4790))))));
/******/ 				register("@x800/shared/data-access", "0.0.0", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_core_angular_core"), __webpack_require__.e("default-webpack_sharing_consume_default_rxjs_operators_rxjs_operators"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_common_angular_common"), __webpack_require__.e("default-webpack_sharing_consume_default_ngx-translate_core_ngx-translate_core"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_common_http_angular_common_http"), __webpack_require__.e("default-webpack_sharing_consume_default_colsen1991_ngx-translate-extract-marker_colsen1991_ng-e79105"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_router_angular_router"), __webpack_require__.e("default-webpack_sharing_consume_default_ngx-permissions_ngx-permissions"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_core_rxjs-interop_angular_core_rxjs-interop"), __webpack_require__.e("default-libs_shared_data-access_src_index_ts")]).then(() => (() => (__webpack_require__(921))))));
/******/ 				register("@x800/shared/ui/components", "0.0.0", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_core_angular_core"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_common_angular_common"), __webpack_require__.e("default-webpack_sharing_consume_default_ngx-translate_core_ngx-translate_core"), __webpack_require__.e("default-webpack_sharing_consume_default_x800_shared_data-access_x800_shared_data-access"), __webpack_require__.e("default-webpack_sharing_consume_default_one_angular_one_angular"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_core_rxjs-interop_angular_core_rxjs-interop"), __webpack_require__.e("default-webpack_sharing_consume_default_date-fns_date-fns"), __webpack_require__.e("default-libs_shared_ui_components_src_index_ts")]).then(() => (() => (__webpack_require__(966))))));
/******/ 				register("@x800/shared/ui/pipes", "0.0.0", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_core_angular_core"), __webpack_require__.e("default-webpack_sharing_consume_default_ngx-translate_core_ngx-translate_core"), __webpack_require__.e("default-webpack_sharing_consume_default_x800_shared_data-access_x800_shared_data-access"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_platform-browser_angular_platform-browser"), __webpack_require__.e("default-webpack_sharing_consume_default_date-fns_date-fns"), __webpack_require__.e("common")]).then(() => (() => (__webpack_require__(495))))));
/******/ 				register("@x800/software-center/data-access", "0.0.0", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_angular_core_angular_core"), __webpack_require__.e("default-webpack_sharing_consume_default_x800_shared_data-access_x800_shared_data-access"), __webpack_require__.e("common"), __webpack_require__.e("node_modules_pnpm_babel_runtime_7_23_2_node_modules_babel_runtime_helpers_esm_asyncToGenerato-62d3ee2")]).then(() => (() => (__webpack_require__(7368))))));
/******/ 				register("@x800/software-center/feature-dismissed-updates-buttons", "0.0.0", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_angular_core_angular_core"), __webpack_require__.e("default-webpack_sharing_consume_default_ngx-translate_core_ngx-translate_core"), __webpack_require__.e("default-webpack_sharing_consume_default_one_angular_one_angular"), __webpack_require__.e("default-webpack_sharing_consume_default_x800_software-center_data-access_x800_software-center-a541de"), __webpack_require__.e("common")]).then(() => (() => (__webpack_require__(2449))))));
/******/ 				register("@x800/software-center/feature-usb-copy-updates-buttons", "0.0.0", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_angular_core_angular_core"), __webpack_require__.e("default-webpack_sharing_consume_default_ngx-translate_core_ngx-translate_core"), __webpack_require__.e("default-webpack_sharing_consume_default_x800_shared_data-access_x800_shared_data-access"), __webpack_require__.e("default-webpack_sharing_consume_default_one_angular_one_angular"), __webpack_require__.e("default-webpack_sharing_consume_default_colsen1991_ngx-translate-extract-marker_colsen1991_ng-e79105"), __webpack_require__.e("default-webpack_sharing_consume_default_x800_software-center_data-access_x800_software-center-a541de"), __webpack_require__.e("default-webpack_sharing_consume_default_x800_shared_ui_components_x800_shared_ui_components"), __webpack_require__.e("common"), __webpack_require__.e("node_modules_pnpm_babel_runtime_7_23_2_node_modules_babel_runtime_helpers_esm_asyncToGenerato-62d3ee3")]).then(() => (() => (__webpack_require__(9743))))));
/******/ 				register("@x800/software-center/ui", "0.0.0", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_angular_core_angular_core"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_common_angular_common"), __webpack_require__.e("default-webpack_sharing_consume_default_ngx-translate_core_ngx-translate_core"), __webpack_require__.e("default-webpack_sharing_consume_default_x800_shared_data-access_x800_shared_data-access"), __webpack_require__.e("default-webpack_sharing_consume_default_one_angular_one_angular"), __webpack_require__.e("default-webpack_sharing_consume_default_x800_shared_ui_components_x800_shared_ui_components"), __webpack_require__.e("default-libs_software-center_ui_src_index_ts")]).then(() => (() => (__webpack_require__(2205))))));
/******/ 				register("date-fns", "2.29.3", () => (__webpack_require__.e("node_modules_pnpm_date-fns_2_29_3_node_modules_date-fns_esm_index_js").then(() => (() => (__webpack_require__(4581))))));
/******/ 				register("ngx-permissions", "16.0.1", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_core_angular_core"), __webpack_require__.e("default-webpack_sharing_consume_default_rxjs_operators_rxjs_operators"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_router_angular_router"), __webpack_require__.e("default-node_modules_pnpm_ngx-permissions_16_0_1__angular_core_17_0_7__angular_router_17_0_7_-dba0f7")]).then(() => (() => (__webpack_require__(9019))))));
/******/ 				register("rxjs/operators", "7.8.1", () => (Promise.all([__webpack_require__.e("default-node_modules_pnpm_rxjs_7_8_1_node_modules_rxjs_dist_esm_internal_operators_auditTime_-a4e86f"), __webpack_require__.e("node_modules_pnpm_rxjs_7_8_1_node_modules_rxjs_dist_esm_operators_index_js")]).then(() => (() => (__webpack_require__(8034))))));
/******/ 				register("rxjs", "7.8.1", () => (Promise.all([__webpack_require__.e("default-node_modules_pnpm_rxjs_7_8_1_node_modules_rxjs_dist_esm_internal_operators_auditTime_-a4e86f"), __webpack_require__.e("node_modules_pnpm_rxjs_7_8_1_node_modules_rxjs_dist_esm_index_js")]).then(() => (() => (__webpack_require__(2272))))));
/******/ 			}
/******/ 			break;
/******/ 		}
/******/ 		if(!promises.length) return initPromises[name] = 1;
/******/ 		return initPromises[name] = Promise.all(promises).then(() => (initPromises[name] = 1));
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/trusted types policy */
/******/ (() => {
/******/ 	var policy;
/******/ 	__webpack_require__.tt = () => {
/******/ 		// Create Trusted Type policy if Trusted Types are available and the policy doesn't exist yet.
/******/ 		if (policy === undefined) {
/******/ 			policy = {
/******/ 				createScriptURL: (url) => (url)
/******/ 			};
/******/ 			if (typeof trustedTypes !== "undefined" && trustedTypes.createPolicy) {
/******/ 				policy = trustedTypes.createPolicy("angular#bundler", policy);
/******/ 			}
/******/ 		}
/******/ 		return policy;
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/trusted types script url */
/******/ (() => {
/******/ 	__webpack_require__.tu = (url) => (__webpack_require__.tt().createScriptURL(url));
/******/ })();
/******/ 
/******/ /* webpack/runtime/publicPath */
/******/ (() => {
/******/ 	var scriptUrl;
/******/ 	if (typeof import.meta.url === "string") scriptUrl = import.meta.url
/******/ 	// When supporting browsers where an automatic publicPath is not supported you must specify an output.publicPath manually via configuration
/******/ 	// or pass an empty string ("") and set the __webpack_public_path__ variable from your code to use your own logic.
/******/ 	if (!scriptUrl) throw new Error("Automatic publicPath is not supported in this browser");
/******/ 	scriptUrl = scriptUrl.replace(/#.*$/, "").replace(/\?.*$/, "").replace(/\/[^\/]+$/, "/");
/******/ 	__webpack_require__.p = scriptUrl;
/******/ })();
/******/ 
/******/ /* webpack/runtime/consumes */
/******/ (() => {
/******/ 	var parseVersion = (str) => {
/******/ 		// see webpack/lib/util/semver.js for original code
/******/ 		var p=p=>{return p.split(".").map((p=>{return+p==p?+p:p}))},n=/^([^-+]+)?(?:-([^+]+))?(?:\+(.+))?$/.exec(str),r=n[1]?p(n[1]):[];return n[2]&&(r.length++,r.push.apply(r,p(n[2]))),n[3]&&(r.push([]),r.push.apply(r,p(n[3]))),r;
/******/ 	}
/******/ 	var versionLt = (a, b) => {
/******/ 		// see webpack/lib/util/semver.js for original code
/******/ 		a=parseVersion(a),b=parseVersion(b);for(var r=0;;){if(r>=a.length)return r<b.length&&"u"!=(typeof b[r])[0];var e=a[r],n=(typeof e)[0];if(r>=b.length)return"u"==n;var t=b[r],f=(typeof t)[0];if(n!=f)return"o"==n&&"n"==f||("s"==f||"u"==n);if("o"!=n&&"u"!=n&&e!=t)return e<t;r++}
/******/ 	}
/******/ 	var rangeToString = (range) => {
/******/ 		// see webpack/lib/util/semver.js for original code
/******/ 		var r=range[0],n="";if(1===range.length)return"*";if(r+.5){n+=0==r?">=":-1==r?"<":1==r?"^":2==r?"~":r>0?"=":"!=";for(var e=1,a=1;a<range.length;a++){e--,n+="u"==(typeof(t=range[a]))[0]?"-":(e>0?".":"")+(e=2,t)}return n}var g=[];for(a=1;a<range.length;a++){var t=range[a];g.push(0===t?"not("+o()+")":1===t?"("+o()+" || "+o()+")":2===t?g.pop()+" "+g.pop():rangeToString(t))}return o();function o(){return g.pop().replace(/^\((.+)\)$/,"$1")}
/******/ 	}
/******/ 	var satisfy = (range, version) => {
/******/ 		// see webpack/lib/util/semver.js for original code
/******/ 		if(0 in range){version=parseVersion(version);var e=range[0],r=e<0;r&&(e=-e-1);for(var n=0,i=1,a=!0;;i++,n++){var f,s,g=i<range.length?(typeof range[i])[0]:"";if(n>=version.length||"o"==(s=(typeof(f=version[n]))[0]))return!a||("u"==g?i>e&&!r:""==g!=r);if("u"==s){if(!a||"u"!=g)return!1}else if(a)if(g==s)if(i<=e){if(f!=range[i])return!1}else{if(r?f>range[i]:f<range[i])return!1;f!=range[i]&&(a=!1)}else if("s"!=g&&"n"!=g){if(r||i<=e)return!1;a=!1,i--}else{if(i<=e||s<g!=r)return!1;a=!1}else"s"!=g&&"n"!=g&&(a=!1,i--)}}var t=[],o=t.pop.bind(t);for(n=1;n<range.length;n++){var u=range[n];t.push(1==u?o()|o():2==u?o()&o():u?satisfy(u,version):!o())}return!!o();
/******/ 	}
/******/ 	var ensureExistence = (scopeName, key) => {
/******/ 		var scope = __webpack_require__.S[scopeName];
/******/ 		if(!scope || !__webpack_require__.o(scope, key)) throw new Error("Shared module " + key + " doesn't exist in shared scope " + scopeName);
/******/ 		return scope;
/******/ 	};
/******/ 	var findVersion = (scope, key) => {
/******/ 		var versions = scope[key];
/******/ 		var key = Object.keys(versions).reduce((a, b) => {
/******/ 			return !a || versionLt(a, b) ? b : a;
/******/ 		}, 0);
/******/ 		return key && versions[key]
/******/ 	};
/******/ 	var findSingletonVersionKey = (scope, key) => {
/******/ 		var versions = scope[key];
/******/ 		return Object.keys(versions).reduce((a, b) => {
/******/ 			return !a || (!versions[a].loaded && versionLt(a, b)) ? b : a;
/******/ 		}, 0);
/******/ 	};
/******/ 	var getInvalidSingletonVersionMessage = (scope, key, version, requiredVersion) => {
/******/ 		return "Unsatisfied version " + version + " from " + (version && scope[key][version].from) + " of shared singleton module " + key + " (required " + rangeToString(requiredVersion) + ")"
/******/ 	};
/******/ 	var getSingleton = (scope, scopeName, key, requiredVersion) => {
/******/ 		var version = findSingletonVersionKey(scope, key);
/******/ 		return get(scope[key][version]);
/******/ 	};
/******/ 	var getSingletonVersion = (scope, scopeName, key, requiredVersion) => {
/******/ 		var version = findSingletonVersionKey(scope, key);
/******/ 		if (!satisfy(requiredVersion, version)) warn(getInvalidSingletonVersionMessage(scope, key, version, requiredVersion));
/******/ 		return get(scope[key][version]);
/******/ 	};
/******/ 	var getStrictSingletonVersion = (scope, scopeName, key, requiredVersion) => {
/******/ 		var version = findSingletonVersionKey(scope, key);
/******/ 		if (!satisfy(requiredVersion, version)) throw new Error(getInvalidSingletonVersionMessage(scope, key, version, requiredVersion));
/******/ 		return get(scope[key][version]);
/******/ 	};
/******/ 	var findValidVersion = (scope, key, requiredVersion) => {
/******/ 		var versions = scope[key];
/******/ 		var key = Object.keys(versions).reduce((a, b) => {
/******/ 			if (!satisfy(requiredVersion, b)) return a;
/******/ 			return !a || versionLt(a, b) ? b : a;
/******/ 		}, 0);
/******/ 		return key && versions[key]
/******/ 	};
/******/ 	var getInvalidVersionMessage = (scope, scopeName, key, requiredVersion) => {
/******/ 		var versions = scope[key];
/******/ 		return "No satisfying version (" + rangeToString(requiredVersion) + ") of shared module " + key + " found in shared scope " + scopeName + ".\n" +
/******/ 			"Available versions: " + Object.keys(versions).map((key) => {
/******/ 			return key + " from " + versions[key].from;
/******/ 		}).join(", ");
/******/ 	};
/******/ 	var getValidVersion = (scope, scopeName, key, requiredVersion) => {
/******/ 		var entry = findValidVersion(scope, key, requiredVersion);
/******/ 		if(entry) return get(entry);
/******/ 		throw new Error(getInvalidVersionMessage(scope, scopeName, key, requiredVersion));
/******/ 	};
/******/ 	var warn = (msg) => {
/******/ 		if (typeof console !== "undefined" && console.warn) console.warn(msg);
/******/ 	};
/******/ 	var warnInvalidVersion = (scope, scopeName, key, requiredVersion) => {
/******/ 		warn(getInvalidVersionMessage(scope, scopeName, key, requiredVersion));
/******/ 	};
/******/ 	var get = (entry) => {
/******/ 		entry.loaded = 1;
/******/ 		return entry.get()
/******/ 	};
/******/ 	var init = (fn) => (function(scopeName, a, b, c) {
/******/ 		var promise = __webpack_require__.I(scopeName);
/******/ 		if (promise && promise.then) return promise.then(fn.bind(fn, scopeName, __webpack_require__.S[scopeName], a, b, c));
/******/ 		return fn(scopeName, __webpack_require__.S[scopeName], a, b, c);
/******/ 	});
/******/ 	
/******/ 	var load = /*#__PURE__*/ init((scopeName, scope, key) => {
/******/ 		ensureExistence(scopeName, key);
/******/ 		return get(findVersion(scope, key));
/******/ 	});
/******/ 	var loadFallback = /*#__PURE__*/ init((scopeName, scope, key, fallback) => {
/******/ 		return scope && __webpack_require__.o(scope, key) ? get(findVersion(scope, key)) : fallback();
/******/ 	});
/******/ 	var loadVersionCheck = /*#__PURE__*/ init((scopeName, scope, key, version) => {
/******/ 		ensureExistence(scopeName, key);
/******/ 		return get(findValidVersion(scope, key, version) || warnInvalidVersion(scope, scopeName, key, version) || findVersion(scope, key));
/******/ 	});
/******/ 	var loadSingleton = /*#__PURE__*/ init((scopeName, scope, key) => {
/******/ 		ensureExistence(scopeName, key);
/******/ 		return getSingleton(scope, scopeName, key);
/******/ 	});
/******/ 	var loadSingletonVersionCheck = /*#__PURE__*/ init((scopeName, scope, key, version) => {
/******/ 		ensureExistence(scopeName, key);
/******/ 		return getSingletonVersion(scope, scopeName, key, version);
/******/ 	});
/******/ 	var loadStrictVersionCheck = /*#__PURE__*/ init((scopeName, scope, key, version) => {
/******/ 		ensureExistence(scopeName, key);
/******/ 		return getValidVersion(scope, scopeName, key, version);
/******/ 	});
/******/ 	var loadStrictSingletonVersionCheck = /*#__PURE__*/ init((scopeName, scope, key, version) => {
/******/ 		ensureExistence(scopeName, key);
/******/ 		return getStrictSingletonVersion(scope, scopeName, key, version);
/******/ 	});
/******/ 	var loadVersionCheckFallback = /*#__PURE__*/ init((scopeName, scope, key, version, fallback) => {
/******/ 		if(!scope || !__webpack_require__.o(scope, key)) return fallback();
/******/ 		return get(findValidVersion(scope, key, version) || warnInvalidVersion(scope, scopeName, key, version) || findVersion(scope, key));
/******/ 	});
/******/ 	var loadSingletonFallback = /*#__PURE__*/ init((scopeName, scope, key, fallback) => {
/******/ 		if(!scope || !__webpack_require__.o(scope, key)) return fallback();
/******/ 		return getSingleton(scope, scopeName, key);
/******/ 	});
/******/ 	var loadSingletonVersionCheckFallback = /*#__PURE__*/ init((scopeName, scope, key, version, fallback) => {
/******/ 		if(!scope || !__webpack_require__.o(scope, key)) return fallback();
/******/ 		return getSingletonVersion(scope, scopeName, key, version);
/******/ 	});
/******/ 	var loadStrictVersionCheckFallback = /*#__PURE__*/ init((scopeName, scope, key, version, fallback) => {
/******/ 		var entry = scope && __webpack_require__.o(scope, key) && findValidVersion(scope, key, version);
/******/ 		return entry ? get(entry) : fallback();
/******/ 	});
/******/ 	var loadStrictSingletonVersionCheckFallback = /*#__PURE__*/ init((scopeName, scope, key, version, fallback) => {
/******/ 		if(!scope || !__webpack_require__.o(scope, key)) return fallback();
/******/ 		return getStrictSingletonVersion(scope, scopeName, key, version);
/******/ 	});
/******/ 	var installedModules = {};
/******/ 	var moduleToHandlerMapping = {
/******/ 		2106: () => (loadStrictSingletonVersionCheckFallback("default", "rxjs", [4,7,8,1], () => (Promise.all([__webpack_require__.e("default-node_modules_pnpm_rxjs_7_8_1_node_modules_rxjs_dist_esm_internal_operators_auditTime_-a4e86f"), __webpack_require__.e("node_modules_pnpm_rxjs_7_8_1_node_modules_rxjs_dist_esm_index_js")]).then(() => (() => (__webpack_require__(2272))))))),
/******/ 		4779: () => (loadStrictSingletonVersionCheckFallback("default", "@angular/core", [4,17,0,7], () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_rxjs_operators_rxjs_operators"), __webpack_require__.e("node_modules_pnpm_angular_core_17_0_7_rxjs_7_8_1_zone_js_0_14_2_node_modules_angular_core_fes-9610d2")]).then(() => (() => (__webpack_require__(6629))))))),
/******/ 		5206: () => (loadStrictSingletonVersionCheckFallback("default", "@angular/common", [4,17,0,7], () => (__webpack_require__.e("default-node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_-3dabbf").then(() => (() => (__webpack_require__(3891))))))),
/******/ 		1874: () => (loadStrictSingletonVersionCheckFallback("default", "@ngx-translate/core", [4,14,0,0], () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_rxjs_operators_rxjs_operators"), __webpack_require__.e("default-node_modules_pnpm_ngx-translate_core_14_0_0__angular_core_17_0_7_rxjs_7_8_1_node_modu-6e2a23")]).then(() => (() => (__webpack_require__(8285))))))),
/******/ 		8735: () => (loadFallback("default", "@x800/shared/data-access", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_rxjs_operators_rxjs_operators"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_common_angular_common"), __webpack_require__.e("default-webpack_sharing_consume_default_ngx-translate_core_ngx-translate_core"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_common_http_angular_common_http"), __webpack_require__.e("default-webpack_sharing_consume_default_colsen1991_ngx-translate-extract-marker_colsen1991_ng-e79105"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_router_angular_router"), __webpack_require__.e("default-webpack_sharing_consume_default_ngx-permissions_ngx-permissions"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_core_rxjs-interop_angular_core_rxjs-interop"), __webpack_require__.e("default-libs_shared_data-access_src_index_ts")]).then(() => (() => (__webpack_require__(921))))))),
/******/ 		1544: () => (loadStrictSingletonVersionCheckFallback("default", "@one/angular", [4,6,10,0], () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_rxjs_operators_rxjs_operators"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_common_angular_common"), __webpack_require__.e("default-node_modules_pnpm_one_angular_6_10_0__one_design-tokens_6_3_0__one_icons_7_7_0__one_r-38e6b8")]).then(() => (() => (__webpack_require__(4790))))))),
/******/ 		9218: () => (loadStrictSingletonVersionCheckFallback("default", "@angular/common/http", [4,17,0,7], () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_rxjs_operators_rxjs_operators"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_common_angular_common"), __webpack_require__.e("default-node_modules_pnpm_angular_common_17_0_7__angular_core_17_0_7_rxjs_7_8_1_node_modules_-38e043")]).then(() => (() => (__webpack_require__(9841))))))),
/******/ 		5276: () => (loadStrictSingletonVersionCheckFallback("default", "@colsen1991/ngx-translate-extract-marker", [4,2,0,8], () => (__webpack_require__.e("node_modules_pnpm_colsen1991_ngx-translate-extract-marker_2_0_8__angular_common_17_0_7__angul-1cc127").then(() => (() => (__webpack_require__(6030))))))),
/******/ 		8679: () => (loadStrictSingletonVersionCheckFallback("default", "@angular/router", [4,17,0,7], () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_rxjs_operators_rxjs_operators"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_common_angular_common"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_platform-browser_angular_platform-browser"), __webpack_require__.e("default-node_modules_pnpm_angular_router_17_0_7__angular_common_17_0_7__angular_core_17_0_7__-f2ac5b")]).then(() => (() => (__webpack_require__(3293))))))),
/******/ 		5497: () => (loadStrictSingletonVersionCheckFallback("default", "ngx-permissions", [4,16,0,1], () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_rxjs_operators_rxjs_operators"), __webpack_require__.e("default-node_modules_pnpm_ngx-permissions_16_0_1__angular_core_17_0_7__angular_router_17_0_7_-dba0f7")]).then(() => (() => (__webpack_require__(9019))))))),
/******/ 		9295: () => (loadFallback("default", "@x800/software-center/data-access", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_x800_shared_data-access_x800_shared_data-access"), __webpack_require__.e("common"), __webpack_require__.e("node_modules_pnpm_babel_runtime_7_23_2_node_modules_babel_runtime_helpers_esm_asyncToGenerato-62d3ee4")]).then(() => (() => (__webpack_require__(7368))))))),
/******/ 		1601: () => (loadFallback("default", "@x800/software-center/feature-dismissed-updates-buttons", () => (__webpack_require__.e("common").then(() => (() => (__webpack_require__(2449))))))),
/******/ 		2541: () => (loadFallback("default", "@x800/software-center/feature-usb-copy-updates-buttons", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_x800_shared_ui_components_x800_shared_ui_components"), __webpack_require__.e("common")]).then(() => (() => (__webpack_require__(9743))))))),
/******/ 		6544: () => (loadFallback("default", "@x800/software-center/ui", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_x800_shared_ui_components_x800_shared_ui_components"), __webpack_require__.e("default-libs_software-center_ui_src_index_ts")]).then(() => (() => (__webpack_require__(2205))))))),
/******/ 		8345: () => (loadStrictSingletonVersionCheckFallback("default", "rxjs/operators", [4,7,8,1], () => (Promise.all([__webpack_require__.e("default-node_modules_pnpm_rxjs_7_8_1_node_modules_rxjs_dist_esm_internal_operators_auditTime_-a4e86f"), __webpack_require__.e("node_modules_pnpm_rxjs_7_8_1_node_modules_rxjs_dist_esm_operators_index_js")]).then(() => (() => (__webpack_require__(8034))))))),
/******/ 		9595: () => (loadStrictSingletonVersionCheckFallback("default", "@angular/core/primitives/signals", [4,17,0,7], () => (__webpack_require__.e("node_modules_pnpm_angular_core_17_0_7_rxjs_7_8_1_zone_js_0_14_2_node_modules_angular_core_fes-a90fed").then(() => (() => (__webpack_require__(125))))))),
/******/ 		5140: () => (loadStrictSingletonVersionCheckFallback("default", "@angular/platform-browser", [4,17,0,7], () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_angular_common_angular_common"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_common_http_angular_common_http"), __webpack_require__.e("default-node_modules_pnpm_angular_platform-browser_17_0_7__angular_animations_17_0_7__angular-0f3a0c")]).then(() => (() => (__webpack_require__(6788))))))),
/******/ 		8973: () => (loadStrictSingletonVersionCheckFallback("default", "@angular/core/rxjs-interop", [4,17,0,7], () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_operators_rxjs_operators"), __webpack_require__.e("common")]).then(() => (() => (__webpack_require__(5314))))))),
/******/ 		5327: () => (loadStrictSingletonVersionCheckFallback("default", "@microsoft/signalr", [4,8,0,0], () => (__webpack_require__.e("default-node_modules_pnpm_microsoft_signalr_8_0_0_node_modules_microsoft_signalr_dist_esm_index_js").then(() => (() => (__webpack_require__(1784))))))),
/******/ 		5957: () => (loadStrictSingletonVersionCheckFallback("default", "date-fns", [4,2,29,3], () => (__webpack_require__.e("node_modules_pnpm_date-fns_2_29_3_node_modules_date-fns_esm_index_js").then(() => (() => (__webpack_require__(4581))))))),
/******/ 		4486: () => (loadFallback("default", "@x800/shared/ui/pipes", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_angular_platform-browser_angular_platform-browser"), __webpack_require__.e("common")]).then(() => (() => (__webpack_require__(495))))))),
/******/ 		9663: () => (loadFallback("default", "@x800/shared/ui/components", () => (Promise.all([__webpack_require__.e("default-webpack_sharing_consume_default_rxjs_rxjs"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_common_angular_common"), __webpack_require__.e("default-webpack_sharing_consume_default_angular_core_rxjs-interop_angular_core_rxjs-interop"), __webpack_require__.e("default-webpack_sharing_consume_default_date-fns_date-fns"), __webpack_require__.e("default-libs_shared_ui_components_src_index_ts")]).then(() => (() => (__webpack_require__(966)))))))
/******/ 	};
/******/ 	// no consumes in initial chunks
/******/ 	var chunkMapping = {
/******/ 		"default-webpack_sharing_consume_default_rxjs_rxjs": [
/******/ 			2106
/******/ 		],
/******/ 		"default-webpack_sharing_consume_default_angular_core_angular_core": [
/******/ 			4779
/******/ 		],
/******/ 		"default-webpack_sharing_consume_default_angular_common_angular_common": [
/******/ 			5206
/******/ 		],
/******/ 		"default-webpack_sharing_consume_default_ngx-translate_core_ngx-translate_core": [
/******/ 			1874
/******/ 		],
/******/ 		"default-webpack_sharing_consume_default_x800_shared_data-access_x800_shared_data-access": [
/******/ 			8735
/******/ 		],
/******/ 		"default-webpack_sharing_consume_default_one_angular_one_angular": [
/******/ 			1544
/******/ 		],
/******/ 		"default-webpack_sharing_consume_default_angular_common_http_angular_common_http": [
/******/ 			9218
/******/ 		],
/******/ 		"default-webpack_sharing_consume_default_colsen1991_ngx-translate-extract-marker_colsen1991_ng-e79105": [
/******/ 			5276
/******/ 		],
/******/ 		"default-webpack_sharing_consume_default_angular_router_angular_router": [
/******/ 			8679
/******/ 		],
/******/ 		"default-webpack_sharing_consume_default_ngx-permissions_ngx-permissions": [
/******/ 			5497
/******/ 		],
/******/ 		"default-webpack_sharing_consume_default_x800_software-center_data-access_x800_software-center-a541de": [
/******/ 			9295
/******/ 		],
/******/ 		"default-webpack_sharing_consume_default_x800_software-center_feature-dismissed-updates-button-4d876f": [
/******/ 			1601,
/******/ 			2541,
/******/ 			6544
/******/ 		],
/******/ 		"default-webpack_sharing_consume_default_rxjs_operators_rxjs_operators": [
/******/ 			8345
/******/ 		],
/******/ 		"node_modules_pnpm_angular_core_17_0_7_rxjs_7_8_1_zone_js_0_14_2_node_modules_angular_core_fes-9610d2": [
/******/ 			9595
/******/ 		],
/******/ 		"default-webpack_sharing_consume_default_angular_platform-browser_angular_platform-browser": [
/******/ 			5140
/******/ 		],
/******/ 		"default-webpack_sharing_consume_default_angular_core_rxjs-interop_angular_core_rxjs-interop": [
/******/ 			8973
/******/ 		],
/******/ 		"default-libs_shared_data-access_src_index_ts": [
/******/ 			5327
/******/ 		],
/******/ 		"default-webpack_sharing_consume_default_date-fns_date-fns": [
/******/ 			5957
/******/ 		],
/******/ 		"default-libs_shared_ui_components_src_index_ts": [
/******/ 			4486
/******/ 		],
/******/ 		"default-webpack_sharing_consume_default_x800_shared_ui_components_x800_shared_ui_components": [
/******/ 			9663
/******/ 		]
/******/ 	};
/******/ 	__webpack_require__.f.consumes = (chunkId, promises) => {
/******/ 		if(__webpack_require__.o(chunkMapping, chunkId)) {
/******/ 			chunkMapping[chunkId].forEach((id) => {
/******/ 				if(__webpack_require__.o(installedModules, id)) return promises.push(installedModules[id]);
/******/ 				var onFactory = (factory) => {
/******/ 					installedModules[id] = 0;
/******/ 					__webpack_require__.m[id] = (module) => {
/******/ 						delete __webpack_require__.c[id];
/******/ 						module.exports = factory();
/******/ 					}
/******/ 				};
/******/ 				var onError = (error) => {
/******/ 					delete installedModules[id];
/******/ 					__webpack_require__.m[id] = (module) => {
/******/ 						delete __webpack_require__.c[id];
/******/ 						throw error;
/******/ 					}
/******/ 				};
/******/ 				try {
/******/ 					var promise = moduleToHandlerMapping[id]();
/******/ 					if(promise.then) {
/******/ 						promises.push(installedModules[id] = promise.then(onFactory)['catch'](onError));
/******/ 					} else onFactory(promise);
/******/ 				} catch(e) { onError(e); }
/******/ 			});
/******/ 		}
/******/ 	}
/******/ })();
/******/ 
/******/ /* webpack/runtime/jsonp chunk loading */
/******/ (() => {
/******/ 	// no baseURI
/******/ 	
/******/ 	// object to store loaded and loading chunks
/******/ 	// undefined = chunk not loaded, null = chunk preloaded/prefetched
/******/ 	// [resolve, reject, Promise] = chunk loading, 0 = chunk loaded
/******/ 	var installedChunks = {
/******/ 		"software-center": 0
/******/ 	};
/******/ 	
/******/ 	__webpack_require__.f.j = (chunkId, promises) => {
/******/ 			// JSONP chunk loading for javascript
/******/ 			var installedChunkData = __webpack_require__.o(installedChunks, chunkId) ? installedChunks[chunkId] : undefined;
/******/ 			if(installedChunkData !== 0) { // 0 means "already installed".
/******/ 	
/******/ 				// a Promise means "currently loading".
/******/ 				if(installedChunkData) {
/******/ 					promises.push(installedChunkData[2]);
/******/ 				} else {
/******/ 					if(!/^default\-webpack_sharing_consume_default_(angular_(co(mmon_(angular_common|http_angular_common_http)|re_(angular_core|rxjs\-interop_angular_core_rxjs\-interop))|(platform\-browser_angular_platform\-brows|router_angular_rout)er)|ngx\-(permissions_ngx\-permissions|translate_core_ngx\-translate_core)|rxjs_(operators_rxjs_operator|rxj)s|x800_s(hared_(data\-access_x800_shared_data\-acces|ui_components_x800_shared_ui_component)s|oftware\-center_(data\-access_x800_software\-center\-a541de|feature\-dismissed\-updates\-button\-4d876f))|colsen1991_ngx\-translate\-extract\-marker_colsen1991_ng\-e79105|date\-fns_date\-fns|one_angular_one_angular)$/.test(chunkId)) {
/******/ 						// setup Promise in chunk cache
/******/ 						var promise = new Promise((resolve, reject) => (installedChunkData = installedChunks[chunkId] = [resolve, reject]));
/******/ 						promises.push(installedChunkData[2] = promise);
/******/ 	
/******/ 						// start chunk loading
/******/ 						var url = __webpack_require__.p + __webpack_require__.u(chunkId);
/******/ 						// create error before stack unwound to get useful stacktrace later
/******/ 						var error = new Error();
/******/ 						var loadingEnded = (event) => {
/******/ 							if(__webpack_require__.o(installedChunks, chunkId)) {
/******/ 								installedChunkData = installedChunks[chunkId];
/******/ 								if(installedChunkData !== 0) installedChunks[chunkId] = undefined;
/******/ 								if(installedChunkData) {
/******/ 									var errorType = event && (event.type === 'load' ? 'missing' : event.type);
/******/ 									var realSrc = event && event.target && event.target.src;
/******/ 									error.message = 'Loading chunk ' + chunkId + ' failed.\n(' + errorType + ': ' + realSrc + ')';
/******/ 									error.name = 'ChunkLoadError';
/******/ 									error.type = errorType;
/******/ 									error.request = realSrc;
/******/ 									installedChunkData[1](error);
/******/ 								}
/******/ 							}
/******/ 						};
/******/ 						__webpack_require__.l(url, loadingEnded, "chunk-" + chunkId, chunkId);
/******/ 					} else installedChunks[chunkId] = 0;
/******/ 				}
/******/ 			}
/******/ 	};
/******/ 	
/******/ 	// no prefetching
/******/ 	
/******/ 	// no preloaded
/******/ 	
/******/ 	// no HMR
/******/ 	
/******/ 	// no HMR manifest
/******/ 	
/******/ 	// no on chunks loaded
/******/ 	
/******/ 	// install a JSONP callback for chunk loading
/******/ 	var webpackJsonpCallback = (parentChunkLoadingFunction, data) => {
/******/ 		var [chunkIds, moreModules, runtime] = data;
/******/ 		// add "moreModules" to the modules object,
/******/ 		// then flag all "chunkIds" as loaded and fire callback
/******/ 		var moduleId, chunkId, i = 0;
/******/ 		if(chunkIds.some((id) => (installedChunks[id] !== 0))) {
/******/ 			for(moduleId in moreModules) {
/******/ 				if(__webpack_require__.o(moreModules, moduleId)) {
/******/ 					__webpack_require__.m[moduleId] = moreModules[moduleId];
/******/ 				}
/******/ 			}
/******/ 			if(runtime) var result = runtime(__webpack_require__);
/******/ 		}
/******/ 		if(parentChunkLoadingFunction) parentChunkLoadingFunction(data);
/******/ 		for(;i < chunkIds.length; i++) {
/******/ 			chunkId = chunkIds[i];
/******/ 			if(__webpack_require__.o(installedChunks, chunkId) && installedChunks[chunkId]) {
/******/ 				installedChunks[chunkId][0]();
/******/ 			}
/******/ 			installedChunks[chunkId] = 0;
/******/ 		}
/******/ 	
/******/ 	}
/******/ 	
/******/ 	var chunkLoadingGlobal = self["webpackChunksoftware_center"] = self["webpackChunksoftware_center"] || [];
/******/ 	chunkLoadingGlobal.forEach(webpackJsonpCallback.bind(null, 0));
/******/ 	chunkLoadingGlobal.push = webpackJsonpCallback.bind(null, chunkLoadingGlobal.push.bind(chunkLoadingGlobal));
/******/ })();
/******/ 
/************************************************************************/
/******/ 
/******/ // module cache are used so entry inlining is disabled
/******/ // startup
/******/ // Load entry module and return exports
/******/ var __webpack_exports__ = __webpack_require__(4720);
/******/ var __webpack_exports__get = __webpack_exports__.get;
/******/ var __webpack_exports__init = __webpack_exports__.init;
/******/ export { __webpack_exports__get as get, __webpack_exports__init as init };
/******/ 
